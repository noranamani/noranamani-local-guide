"""Offline contract tests for the free, privacy-preserving travel calculator."""
import json
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

from localguide.travel_budget import BUDGET_JS, BUDGET_STYLE, budget_body
from localguide.site import Document, STYLE

ROOT = Path(__file__).resolve().parents[1]


class InputIDs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicates = []
    def handle_starttag(self, tag, attrs):
        value = dict(attrs).get("id")
        if value:
            if value in self.ids:
                self.duplicates.append(value)
            self.ids.add(value)


class TravelBudgetTests(unittest.TestCase):
    def test_accessible_markup_and_no_assumed_discounts(self):
        body = budget_body()
        parser = InputIDs()
        parser.feed(body)
        self.assertFalse(parser.duplicates)
        self.assertIn("budget-total", parser.ids)
        self.assertIn("budget-reset", parser.ids)
        self.assertIn('id="budget-include-tickets"', body)
        self.assertIn("割引は自動判定しません", body)
        self.assertIn("送信・保存しません", body)
        self.assertIn('href="travel.html"', body)
        self.assertIn('<script src="travel-budget.js" defer></script>', body)
        for key in ("adult", "high", "middle", "elementary", "preschool"):
            self.assertIn("budget-count-" + key, parser.ids)
            self.assertIn("budget-unit-" + key, parser.ids)
            self.assertIn("budget-discount-count-" + key, parser.ids)
            self.assertIn("budget-discount-unit-" + key, parser.ids)

    def test_site_validator_accepts_only_reviewed_local_script(self):
        valid = Document()
        valid.feed('<html><head><title>試算</title><meta charset="utf-8">'
                   '<meta name="viewport" content="width=device-width, initial-scale=1">'
                   '<meta name="description" content="試算"></head><body>'
                   '<h1>試算</h1><script src="travel-budget.js" defer></script></body></html>')
        valid.close()
        self.assertFalse(valid.errors)
        self.assertIn("travel-budget.js", valid.links)
        for html in (
            '<script>alert(1)</script>',
            '<script src="https://example.com/untrusted.js"></script>',
            '<script src="travel-budget.js" async></script>',
            '<form></form>',
        ):
            with self.subTest(html=html):
                p = Document()
                p.feed(html)
                p.close()
                self.assertTrue(p.errors)
        self.assertIn(".budget-layout", STYLE)
        self.assertIn("@media (max-width: 770px)", BUDGET_STYLE)

    @unittest.skipUnless(shutil.which("node"), "Node.js not installed")
    def test_actual_javascript_math_and_validation(self):
        # Run the shipped JavaScript itself, not a reimplementation in Python.
        js = r"""
const assert = require('node:assert/strict');
const calculate = module.exports.calculateBudget;
function basic() {
  return {
    includeTickets: true,
    tiers: [
      {key:'adult',label:'大人',count:2,unit:1500,discountCount:1,discountUnit:750},
      {key:'high',label:'高校生',count:1,unit:1000,discountCount:0,discountUnit:null},
      {key:'middle',label:'中学生',count:1,unit:800,discountCount:1,discountUnit:0},
      {key:'elementary',label:'小学生',count:2,unit:500,discountCount:1,discountUnit:0},
      {key:'preschool',label:'未就学児',count:0,unit:null,discountCount:0,discountUnit:null},
    ],
    distance:300,economy:15,fuelUnitPrice:170,toll:2500,parking:700,
    transit:0,stay:26400,food:9000,otherTickets:1200,other:2000,target:50000
  };
}
const value = calculate(basic());
assert.equal(value.people, 6);
assert.equal(value.fuel, 3400);
assert.equal(value.savings, 2050);
assert.equal(value.normalTotal, 51000);
assert.equal(value.total, 48950);
assert.equal(value.perPerson, 8158);
assert.equal(value.targetDifference, 1050);
let noTicket = basic(); noTicket.includeTickets=false;
assert.equal(calculate(noTicket).savings, 0);
assert.equal(calculate(noTicket).tickets, 1200);
let zero = basic(); zero.tiers.forEach(x=>x.count=0);
assert.throws(()=>calculate(zero),/1人以上/);
let bad = basic(); bad.tiers[0].discountCount=3;
assert.throws(()=>calculate(bad),/割引対象人数/);
bad = basic(); bad.tiers[0].discountUnit=1501;
assert.throws(()=>calculate(bad),/通常料金を超え/);
bad = basic(); bad.economy=0;
assert.throws(()=>calculate(bad),/燃費/);
bad = basic(); bad.food=-10;
assert.throws(()=>calculate(bad),/食費/);
bad = basic(); bad.distance=0; bad.fuelUnitPrice=null;
assert.equal(calculate(bad).fuel, 0);
console.log('Calculator math checks passed');
"""
        result = subprocess.run(["node", "-e", BUDGET_JS + "\n" + js],
                                capture_output=True, text=True, timeout=15, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
