"""An entirely client-side family-trip cost estimator for Harima Yorimichi.

The visitor supplies all prices and eligibility. No facility fee, disability
discount or total booking quote is inferred from an unverified source.
"""

FARE_CATEGORIES = (
    ("adult", "大人", 2),
    ("high", "高校生", 0),
    ("middle", "中学生", 0),
    ("elementary", "小学生", 2),
    ("preschool", "未就学児", 0),
)

BUDGET_STYLE = """
/* Family trip budget calculator: local component styles only. */
.budget-intro { max-width: 72ch; margin: 0 0 1.3rem; }
.budget-intro .budget-eyebrow { color: #256451; font-weight: 800; letter-spacing: .07em; }
.budget-layout { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(265px, .9fr); gap: 1.3rem; align-items: start; }
.budget-entry { display: grid; gap: 1.2rem; min-width: 0; }
.budget-panel, .budget-result { border: 1px solid #d8e6db; border-radius: 18px; background: #fffefa; padding: clamp(1rem, 3vw, 1.4rem); min-width: 0; }
.budget-panel legend { font-size: 1.14rem; font-weight: 800; padding: 0 .35rem; }
.budget-panel p { margin: .45rem 0 1rem; }
.budget-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .85rem; }
.budget-field { display: flex; flex-direction: column; min-width: 0; gap: .25rem; font-size: .92rem; font-weight: 650; }
.budget-field input { display: block; width: 100%; min-width: 0; border: 1px solid #9aafa2; border-radius: 8px; background: white; padding: .65rem .6rem; font: inherit; color: #203a34; }
.budget-field input:focus-visible, .budget-reset:focus-visible { outline: 3px solid #a35f0b; outline-offset: 2px; }
.budget-field small { font-size: .75rem; font-weight: 400; color: #526a61; }
.budget-fare { border: 1px solid #e1e8df; border-radius: 12px; margin: .8rem 0 0; padding: .85rem; }
.budget-fare legend { font-size: 1rem; font-weight: 700; }
.budget-fare-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .6rem; }
.budget-checkbox { display: flex; gap: .65rem; align-items: center; font-weight: 800; cursor: pointer; }
.budget-checkbox input { inline-size: 1.25rem; block-size: 1.25rem; accent-color: #096858; flex: none; }
.budget-tickets[disabled] { opacity: .5; }
.budget-muted { color: #526a61; font-size: .85rem; }
.budget-result { position: sticky; top: 1rem; background: #f0f7f0; }
.budget-result h2 { margin: 0 0 .6rem; }
.budget-amount { font-size: clamp(1.7rem, 5vw, 2.55rem); line-height: 1.3; font-weight: 850; color: #075847; font-variant-numeric: tabular-nums; }
.budget-result dl { display: grid; grid-template-columns: minmax(0,1fr) auto; gap: .6rem .5rem; margin: 1.1rem 0; }
.budget-result dt { color: #3a594b; }
.budget-result dd { margin: 0; font-weight: 800; text-align: right; font-variant-numeric: tabular-nums; }
.budget-result .budget-rule { border-top: 1px solid #cadccd; padding-top: .7rem; }
.budget-savings { color: #075847; }
.budget-alert { min-height: 2.5rem; font-size: .86rem; }
.budget-alert[data-error="true"] { color: #a02e27; font-weight: 700; }
.budget-reset { display: inline-block; border: 1px solid #789a88; background: #fff; border-radius: 9px; padding: .65rem 1rem; font: inherit; font-weight: 750; color: #075847; cursor: pointer; }
.budget-related { max-width: 72ch; margin-top: 1.5rem; }
.budget-related h2 { margin-top: 0; }
@media (max-width: 770px) {
 .budget-layout { grid-template-columns: minmax(0, 1fr); }
 .budget-result { position: static; }
}
@media (max-width: 430px) {
 .budget-fare-fields { grid-template-columns: repeat(2, minmax(0, 1fr)); }
 .budget-fields { gap: .65rem; }
 .budget-panel, .budget-result { padding: 1rem .85rem; }
}
"""

BUDGET_JS = r"""
/* Offline cost calculator. Never fetches, stores or transmits user input. */
(function () {
  "use strict";
  var CATEGORY_KEYS = ["adult", "high", "middle", "elementary", "preschool"];
  var MAX_COUNT = 99, MAX_MONEY = 100000000;

  function number(value, label, maximum, isInteger) {
    if (value === null || value === undefined || value === "") {
      throw new Error(label + "を入力してください。");
    }
    var n = Number(value);
    if (!Number.isFinite(n) || n < 0 || n > maximum || (isInteger && !Number.isInteger(n))) {
      throw new Error(label + "は有効な0以上の数値で入力してください。");
    }
    return n;
  }

  function amount(value, label) {
    return number(value === null ? 0 : value, label, MAX_MONEY, false);
  }

  function calculateBudget(data) {
    if (!data || !Array.isArray(data.tiers) || data.tiers.length !== CATEGORY_KEYS.length) {
      throw new Error("人数データが不正です。");
    }
    var people = 0, regular = 0, savings = 0;
    data.tiers.forEach(function (item, index) {
      if (!item || item.key !== CATEGORY_KEYS[index]) {
        throw new Error("料金区分の並びが不正です。");
      }
      var count = number(item.count, item.label + "の人数", MAX_COUNT, true);
      people += count;
      if (!data.includeTickets) { return; }
      if (count === 0) { return; }
      var unit = number(item.unit, item.label + "の通常入場料", MAX_MONEY, false);
      var discountCount = number(item.discountCount, item.label + "の割引対象人数", count, true);
      if (discountCount > count) {
        throw new Error(item.label + "の割引対象人数が人数を超えています。");
      }
      var discountUnit = discountCount > 0
        ? number(item.discountUnit, item.label + "の割引後入場料", MAX_MONEY, false)
        : unit;
      if (discountUnit > unit) {
        throw new Error(item.label + "の割引後入場料が通常料金を超えています。");
      }
      regular += count * unit;
      savings += discountCount * (unit - discountUnit);
    });
    if (people === 0) { throw new Error("旅行する人数を1人以上にしてください。"); }

    var distance = number(data.distance, "往復走行距離", 1000000, false);
    var fuel = 0;
    if (distance > 0) {
      var economy = number(data.economy, "燃費", 1000, false);
      if (economy === 0) { throw new Error("燃費は0より大きくしてください。"); }
      var unitPrice = number(data.fuelUnitPrice, "ガソリン単価", 10000, false);
      if (unitPrice === 0) { throw new Error("走行距離を入力した場合はガソリン単価も入力してください。"); }
      fuel = Math.round(distance / economy * unitPrice);
    }
    var toll = amount(data.toll, "高速・有料道路代");
    var parking = amount(data.parking, "駐車場代");
    var transit = amount(data.transit, "その他交通費");
    var stay = amount(data.stay, "宿泊費");
    var food = amount(data.food, "食費");
    var otherTickets = amount(data.otherTickets, "その他の施設料金");
    var other = amount(data.other, "その他の費用");
    var normalTotal = fuel + toll + parking + transit + stay + food + otherTickets + other + regular;
    var total = normalTotal - savings;
    var target = data.target === null ? null : amount(data.target, "目標予算");
    return {
      people: people,
      normalTotal: Math.round(normalTotal),
      total: Math.round(total),
      savings: Math.round(savings),
      perPerson: Math.round(total / people),
      targetDifference: target === null ? null : Math.round(target - total),
      fuel: fuel,
      road: toll + parking,
      transit: transit,
      stay: stay,
      food: food,
      tickets: regular - savings + otherTickets,
      other: other
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports.calculateBudget = calculateBudget;
  }
  if (typeof document === "undefined") { return; }

  var labels = {
    adult: "大人", high: "高校生", middle: "中学生",
    elementary: "小学生", preschool: "未就学児"
  };
  function el(id) { return document.getElementById(id); }
  function read(id) {
    var raw = el(id).value.trim();
    return raw === "" ? null : Number(raw);
  }
  function readOrZero(id) {
    var value = read(id);
    return value === null ? 0 : value;
  }
  function yen(value) {
    return Math.round(value).toLocaleString("ja-JP") + "円";
  }
  function inputData() {
    return {
      includeTickets: el("budget-include-tickets").checked,
      tiers: CATEGORY_KEYS.map(function (key) {
        return {
          key: key, label: labels[key],
          count: readOrZero("budget-count-" + key),
          unit: read("budget-unit-" + key),
          discountCount: readOrZero("budget-discount-count-" + key),
          discountUnit: read("budget-discount-unit-" + key)
        };
      }),
      distance: readOrZero("budget-distance"),
      economy: read("budget-economy"),
      fuelUnitPrice: read("budget-fuel-price"),
      toll: readOrZero("budget-toll"),
      parking: readOrZero("budget-parking"),
      transit: readOrZero("budget-transit"),
      stay: readOrZero("budget-stay"),
      food: readOrZero("budget-food"),
      otherTickets: readOrZero("budget-other-tickets"),
      other: readOrZero("budget-other"),
      target: read("budget-target")
    };
  }
  function update() {
    var status = el("budget-alert");
    var outputs = ["total", "normal", "savings", "person", "fuel", "road",
                   "transit-cost", "stay-cost", "food-cost", "ticket-cost", "other-cost"];
    try {
      var result = calculateBudget(inputData());
      el("budget-total").textContent = yen(result.total);
      el("budget-normal").textContent = yen(result.normalTotal);
      el("budget-savings").textContent = yen(result.savings);
      el("budget-person").textContent = yen(result.perPerson);
      el("budget-fuel").textContent = yen(result.fuel);
      el("budget-road").textContent = yen(result.road);
      el("budget-transit-cost").textContent = yen(result.transit);
      el("budget-stay-cost").textContent = yen(result.stay);
      el("budget-food-cost").textContent = yen(result.food);
      el("budget-ticket-cost").textContent = yen(result.tickets);
      el("budget-other-cost").textContent = yen(result.other);
      el("budget-target-result").textContent = result.targetDifference === null
        ? "未設定" : (result.targetDifference >= 0
          ? "予算内・残り" + yen(result.targetDifference)
          : "予算超過・" + yen(-result.targetDifference));
      status.dataset.error = "false";
      status.textContent = (result.people + "人分・入力した項目のみの概算です。" +
        (inputData().includeTickets
          ? "施設ごとの割引対象条件は公式案内で確認してください。"
          : "施設入場料の年齢区分別計算は対象外です。"));
    } catch (error) {
      outputs.forEach(function (name) { el("budget-" + name).textContent = "—"; });
      el("budget-target-result").textContent = "—";
      status.dataset.error = "true";
      status.textContent = error.message;
    }
  }
  function init() {
    var ticketToggle = el("budget-include-tickets");
    if (!ticketToggle) { return; }
    function changed() {
      el("budget-tickets").disabled = !ticketToggle.checked;
      update();
    }
    document.querySelectorAll(".budget-entry input").forEach(function (input) {
      input.addEventListener("input", update);
      input.addEventListener("change", changed);
    });
    el("budget-reset").addEventListener("click", function () {
      document.querySelectorAll(".budget-entry input[type=number]").forEach(function (input) {
        input.value = input.defaultValue;
      });
      ticketToggle.checked = false;
      changed();
    });
    changed();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
}());
"""


def _number_input(identifier, label, default="", *, step="1", placeholder="0"):
    """Only fixed field names and numeric defaults are used in generated markup."""
    value = f' value="{default}"' if default != "" else ""
    return (
        f'<label class="budget-field" for="budget-{identifier}">{label}'
        f'<input id="budget-{identifier}" type="number" min="0" step="{step}"'
        f' placeholder="{placeholder}" inputmode="decimal"{value}></label>'
    )


def budget_body(travel_available=True, nearby_available=True):
    persons = "".join(
        _number_input("count-" + key, label + "（人）", str(default))
        for key, label, default in FARE_CATEGORIES
    )
    fees = "".join(
        '<fieldset class="budget-fare"><legend>' + label + '</legend>'
        '<div class="budget-fare-fields">'
        + _number_input("unit-" + key, "通常料金（1人・円）", "")
        + _number_input("discount-count-" + key, "割引対象（人）", "0")
        + _number_input("discount-unit-" + key, "割引後料金（1人・円）", "")
        + '</div></fieldset>'
        for key, label, _ in FARE_CATEGORIES
    )
    return (
        '<div class="budget-intro">'
        '<p class="budget-eyebrow">FREE TOOL / 家族のおでかけ予算</p>'
        '<p>車での移動、宿泊、食費、入場料をまとめて計算。'
        '施設の割引対象者や付き添いの条件を確認したうえで、割引後の料金も比較できます。</p>'
        '<p class="budget-muted">入力内容はこの端末内だけで計算し、送信・保存しません。'
        '金額はすべてご自身で入力してください。未入力の費用は合計に含まれません。</p>'
        '</div>'
        '<div class="budget-layout"><div class="budget-entry" aria-label="旅行費用の入力">'
        '<fieldset class="budget-panel"><legend>1. 一緒に旅行する人数</legend>'
        '<p class="budget-muted">年齢区分は入力の目安です。実際の施設料金区分とは異なることがあります。</p>'
        '<div class="budget-fields">' + persons + '</div></fieldset>'
        '<fieldset class="budget-panel"><legend>2. 交通・宿泊・食事など</legend>'
        '<p class="budget-muted">燃費は15km/Lを仮入力しています。'
        '現在のガソリン単価と実車の燃費に合わせて変更してください。'
        '宿泊費は家族全員・全室・全泊の合計額を入力します。</p>'
        '<div class="budget-fields">'
        + _number_input("distance", "車の往復距離（km）", "", step="any")
        + _number_input("economy", "燃費（km/L）", "15", step="any")
        + _number_input("fuel-price", "ガソリン単価（円/L）", "", step="any")
        + _number_input("toll", "高速・有料道路代（円）", "")
        + _number_input("parking", "駐車場代（円）", "")
        + _number_input("transit", "電車・バス等（合計・円）", "")
        + _number_input("stay", "宿泊費（家族合計・円）", "")
        + _number_input("food", "食費（旅行全体・円）", "")
        + _number_input("other-tickets", "別施設の入場料（合計・円）", "")
        + _number_input("other", "お土産・雑費（合計・円）", "")
        + _number_input("target", "目標予算（任意・円）", "")
        + '</div></fieldset>'
        '<section class="budget-panel" aria-labelledby="budget-tickets-title">'
        '<h2 id="budget-tickets-title">3. 施設の入場料・割引（任意）</h2>'
        '<p class="budget-muted">1施設分の入場料を人数別に計算。'
        '利用しない場合はチェックを入れず、入場料は計算対象外にしてください。'
        'チェックした場合、人数がいる区分の通常料金を0円（無料）も含めて入力してください。</p>'
        '<label class="budget-checkbox" for="budget-include-tickets">'
        '<input type="checkbox" id="budget-include-tickets">この施設の入場料を計算する</label>'
        '<fieldset id="budget-tickets" class="budget-tickets" disabled>'
        '<legend class="budget-muted">対象者・付き添いを含む割引人数は施設の公式案内で確認</legend>'
        + fees
        + '</fieldset><p class="budget-muted">割引人数が1人以上の場合のみ、'
        'その区分の「割引後料金」を入力してください。'
        '障害者手帳、子ども料金、付き添いの割引は自動判定しません。</p>'
        '</section>'
        '<button id="budget-reset" class="budget-reset" type="button">入力を初期化</button>'
        '</div><aside class="budget-result" aria-labelledby="budget-result-title">'
        '<h2 id="budget-result-title">旅行費用の概算</h2>'
        '<p class="budget-muted">割引を反映した合計</p>'
        '<div id="budget-total" class="budget-amount" aria-live="polite" aria-atomic="true">—</div>'
        '<dl>'
        '<dt>割引なしの合計</dt><dd id="budget-normal">—</dd>'
        '<dt>施設の割引額</dt><dd class="budget-savings" id="budget-savings">—</dd>'
        '<dt>1人あたり</dt><dd id="budget-person">—</dd>'
        '<dt class="budget-rule">ガソリン代</dt><dd class="budget-rule" id="budget-fuel">—</dd>'
        '<dt>高速代・駐車場代</dt><dd id="budget-road">—</dd>'
        '<dt>その他交通費</dt><dd id="budget-transit-cost">—</dd>'
        '<dt>宿泊費</dt><dd id="budget-stay-cost">—</dd>'
        '<dt>食費</dt><dd id="budget-food-cost">—</dd>'
        '<dt>施設入場料</dt><dd id="budget-ticket-cost">—</dd>'
        '<dt>その他</dt><dd id="budget-other-cost">—</dd>'
        '<dt class="budget-rule">目標予算との差</dt>'
        '<dd class="budget-rule" id="budget-target-result">—</dd>'
        '</dl><p id="budget-alert" class="budget-alert" role="status" aria-live="polite"></p>'
        '<p class="budget-muted">試算は予約・料金を保証しません。'
        '宿泊、年齢区分、割引の対象・証明方法は各施設の公式案内で最終確認してください。</p>'
        '</aside></div>'
        + ('<section class="notice budget-related"><h2>次は行き先を探す</h2>'
           + ('<p><a href="travel.html">家族旅行プランを見る</a>（旅行記事には広告・PRを含む場合があります）</p>'
              if travel_available else '')
           + ('<p><a href="nearby.html">近場のよりみちガイドを見る</a></p>'
              if nearby_available else '')
           + '</section>' if travel_available or nearby_available else '')
        + '<script src="travel-budget.js" defer></script>'
    )
