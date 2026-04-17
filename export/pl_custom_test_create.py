"""
Run with:
    bench --site local.site execute export.pl_custom_test_create.create_print_format
"""

PRINT_FORMAT_NAME = "PL Custom - Test Item Subitem Distribution"

HTML = r"""<style>
* { box-sizing: border-box; margin: 0; padding: 0; }

  @page {
    size: A4;
    margin: 2mm;
  }

  .print-format,
  .print-format-preview {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
  }

  .pl-wrap {
      font-family: Arial, sans-serif;
      font-size: 8.5pt;
      color: #000;
      width: 100%;
      max-width: 100%;
      border: 1.5px solid #000;
      padding: 0;
      margin: 0;
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
  }

  .pl-header {
    display: table;
    width: 100%;
    margin-bottom: 6px;
  }

  .pl-header-left {
    display: table-cell;
    width: 42%;
    vertical-align: top;
    padding: 2px 4px 0 4px;
  }

  .pl-header-center {
    display: table-cell;
    width: 18%;
    vertical-align: top;
    text-align: center;
    padding-top: 2px;
  }

  .pl-header-right {
    display: table-cell;
    width: 40%;
    vertical-align: top;
    padding: 0;
  }

  .company-name {
    font-size: 9pt;
    font-weight: bold;
    margin-top: 2px;
  }

  .company-addr {
    font-size: 6.7pt;
    color: #333;
    line-height: 1.3;
    margin-top: 2px;
  }

  .pl-title {
    font-size: 13pt;
    font-weight: bold;
    color: #5083be;
    line-height: 1.1;
    white-space: nowrap;
  }

  .meta-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7pt;
    border: 1px solid #000;
  }

  .meta-table td {
    padding: 5px 6px;
    border: 1px solid #000;
    vertical-align: middle;
  }

  .meta-table td:first-child {
    font-weight: bold;
    background-color: #d9d9d9;
    color: #000;
    width: 95px;
    white-space: nowrap;
  }

  .meta-table td:last-child {
    background-color: #fff;
    color: #000;
  }

  .addr-section {
    display: table;
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 6px;
  }

  .addr-cell {
    display: table-cell;
    width: 25%;
    vertical-align: top;
    padding: 5px 7px 6px 7px;
    font-size: 7pt;
    line-height: 1.35;
  }

  .addr-cell:last-child { border-right: none; }

  .addr-title {
    font-weight: bold;
    font-size: 5.7pt;
    color: #fff;
    background-color: #5083be !important;
    margin: -5px -7px 5px -7px;
    padding: 3px 7px;
    text-transform: uppercase;
    line-height: 1.2;
  }

  .addr-name {
    font-weight: bold;
  }

  .ship-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 7pt;
  }

  .ship-table td {
    padding: 2px 0;
    vertical-align: top;
    line-height: 1.35;
  }

  .ship-table td:first-child {
    font-weight: bold;
    color: #1a3a6b;
    white-space: nowrap;
    padding-right: 4px;
    width: 52%;
  }

  .items-table {
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 6px;
      table-layout: fixed;
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
  }

    .items-table tbody td,
    .items-table thead th {
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
    }

    .items-table col.c-box      { width: 5%; }
.items-table col.c-cust     { width: 9.5%; }
.items-table col.c-gmei     { width: 9.5%; }
.items-table col.c-desc     { width: 16.5%; }
.items-table col.c-qty      { width: 5.8%; }
.items-table col.c-tqty     { width: 6.2%; }
.items-table col.c-uwt      { width: 6.5%; }
.items-table col.c-nwt      { width: 6.5%; }
.items-table col.c-gwt      { width: 6.5%; }
.items-table col.c-l        { width: 4.8%; }
.items-table col.c-w        { width: 4.8%; }
.items-table col.c-h        { width: 4.8%; }
.items-table col.c-cbf      { width: 5.8%; }
.items-table col.c-cbm      { width: 5.8%; }
.items-table col.c-boxtype  { width: 7%; }

  .items-table thead th {
  background-color: #5083be !important;
  color: #fff !important;
  border: 1px solid #000;
  text-align: center;
  vertical-align: middle !important;
  font-size: 5pt;
  font-weight: bold;
  line-height: 1.05;
  padding: 2px 2px;
  white-space: normal;
  word-break: keep-all;
  overflow-wrap: normal;
  height: 42px;
}

.items-table thead th .th-wrap {
  display: table-cell;
  width: 100%;
  height: 52px;
  vertical-align: middle;
  text-align: center;
  line-height: 1.1;
  padding: 6px 1px 6px 1px;
}

.items-table thead th.tight .th-wrap {
  font-size: 5pt;
  line-height: 1.05;
}


  .items-table tbody td {
  padding: 4px 2px;
  border: 1px solid #000;
  vertical-align: middle;
  font-size: 6.7pt;
  line-height: 1.15;
  word-wrap: normal;
  overflow-wrap: normal;
  word-break: normal;
}

 /* default center alignment */
.items-table tbody td.tc,
.items-table tbody td.tr,
.box-cell,
.items-table tbody td[rowspan] {
  text-align: center !important;
  vertical-align: middle !important;
}

/* keep only box + numeric/rowspan values in one line */
.box-cell,
.items-table tbody td[rowspan],
.items-table tbody td:nth-child(5),
.items-table tbody td:nth-child(6),
.items-table tbody td:nth-child(7),
.items-table tbody td:nth-child(8),
.items-table tbody td:nth-child(9),
.items-table tbody td:nth-child(10),
.items-table tbody td:nth-child(11),
.items-table tbody td:nth-child(12),
.items-table tbody td:nth-child(13),
.items-table tbody td:nth-child(14),
.items-table tbody td:nth-child(15) {
  white-space: nowrap !important;
  word-break: keep-all !important;
  overflow-wrap: normal !important;
}

.items-table tbody td:nth-child(8) {
    text-align: left !important;
}

/* allow wrapping for Customer Part No and GMEI Part */
.items-table tbody td:nth-child(2),
.items-table tbody td:nth-child(3) {
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: anywhere !important;
  line-height: 1.15;
}

.items-table tbody td:nth-child(4) {
  white-space: normal !important;
  word-break: break-word !important;
  overflow-wrap: break-word !important;
}

  .total-row td {
  background-color: #5083be !important;
  color: #ffffff !important;
  font-weight: bold;
  text-align: center;
  border: 1px solid #1a3a6b !important;
  padding: 5px 3px !important;
  font-size: 7pt;
}

  .pl-footer {
    width: 100%;
    display: table;
    min-height: 50px;
  }

  .pl-footer-left {
    display: table-cell;
    width: 60%;
    font-size: 7pt;
    vertical-align: top !important;
    font-style: italic;
    padding: 2px 4px 0 4px;
  }

  .pl-footer-right {
    display: table-cell;
    width: 40%;
    text-align: center;
    font-size: 8pt;
    vertical-align: bottom;
  }

  .sig-line {
    margin-top: 35px;
    border-top: 1px solid #000;
    padding-top: 4px;
    font-weight: bold;
    width: 180px;
    margin-left: auto;
  }

  /* Prevent page breaks inside table rows and rowspan groups */
    .items-table tr {
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .items-table tbody {
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .items-table {
      page-break-inside: auto;
    }

    /* Keep header and footer together */
    .pl-header {
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .addr-section {
      page-break-inside: avoid;
      break-inside: avoid;
    }

    .pl-footer {
      page-break-inside: avoid;
      break-inside: avoid;
      page-break-before: avoid;
      break-before: avoid;
    }

    /* Repeat table header on each page */
    .items-table thead {
      display: table-header-group;
    }

    .items-table tbody td {
  text-align: left !important;
}

/* Subitem rows: slight indent on description column */
.items-table tbody tr.subitem-row td:nth-child(4) {
  padding-left: 10px;
}

</style>

{%- set dn = frappe.get_doc("Delivery Note", doc.delivery_note) -%}
{%- set pt = frappe.get_doc("Delivery Note", doc.tc_name) -%}
{%- set customer = frappe.get_doc("Customer", dn.customer) if dn.customer else None -%}
{%- set cust_address = frappe.get_doc("Address", dn.customer_address) if dn.customer_address else None -%}
{%- set company_address = frappe.get_doc("Address", dn.company_address) if dn.company_address else None -%}
{% set shipping_address = frappe.get_doc("Address", dn.shipping_address_name) if dn.shipping_address_name else None %}
{% set shipping_address_text = (dn.shipping_address or "") %}
{%- set ns = namespace(short_name="", total_qty=0, total_net_weight=0, total_gross_weight=0, total_cbf=0, total_cbm=0) -%}
{%- set so_name = dn.items[0].against_sales_order if dn.items and dn.items[0].against_sales_order else None -%}
{%- set so = frappe.get_doc("Sales Order", so_name) if so_name else None -%}
{%- set si_name = frappe.db.get_value("Sales Invoice Item", {"delivery_note": dn.name}, "parent") -%}
{%- set si = frappe.get_doc("Sales Invoice", si_name) if si_name else None -%}


{%- if dn.customer_name -%}
    {%- for w in dn.customer_name.split(" ") if w|length > 0 -%}
        {%- set ns.short_name = ns.short_name + w[0] -%}
    {%- endfor -%}
{%- endif -%}

{# ── BUILD items_for_group: same as PL Custom + custom_row_uid added ── #}
{%- set items_for_group = [] -%}
{%- for row in doc.items -%}
  {%- set _ = items_for_group.append({
    "custom_box":          row.custom_box if row.custom_box else "NO_BOX",
    "item_code":           row.item_code,
    "description":         row.description,
    "item_name":           row.item_name,
    "qty":                 row.qty,
    "custom_unit_weight":  row.custom_unit_weight,
    "custom__gross_weight":row.custom__gross_weight,
    "custom_length":       row.custom_length,
    "custom_width":        row.custom_width,
    "custom_height":       row.custom_height,
    "custom_cubic_feet":   row.custom_cubic_feet,
    "custom_cubic_meter":  row.custom_cubic_meter,
    "custom_box_type":     row.custom_box_type,
    "custom_row_uid":      row.custom_row_uid
  }) -%}
{%- endfor -%}

{%- set grouped = items_for_group | groupby("custom_box") | list -%}
{%- set total_boxes = grouped | length -%}

<div class="pl-wrap">

  <div class="pl-header">

    <div class="pl-header-left">
      <table style="border-collapse:collapse; width:100%;">
        <tr>
          <td style="width:70px; vertical-align:top;">
            <img src="/files/GME.png" style="max-height:55px; max-width:65px;">
          </td>
        </tr>
        <tr>
          <td>
            <div class="company-name">
              Global Mining Equipments
            </div>
          </td>
        </tr>
        <tr>
          <td>
            <div class="company-addr">
              {{ dn.company_address_display | safe }}
            </div>
          </td>
        </tr>
      </table>
    </div>

    <div class="pl-header-center">
      <div class="pl-title">Packing List</div>
    </div>

    {% set dn_date = frappe.get_doc("Delivery Note",doc.delivery_note) %}
    <div class="pl-header-right">
      <table class="meta-table">
          <tr>
            <td>Packing Slip</td>
            <td>{{ doc.name }}</td>
          </tr>
          <tr>
            <td>Date</td>
            <td>{{ frappe.utils.formatdate(dn_date.posting_date, "dd-MM-yyyy") }}</td>
          </tr>
          <tr>
            <td>PO #</td>
            <td>{{ dn.po_no }}</td>
          </tr>
          {% if si %}
          <tr>
            <td>Invoice No & Date</td>
            <td>{{ si.name }}{% if si.posting_date %} / {{ frappe.utils.formatdate(si.posting_date, "dd-MM-yyyy") }}{% endif %}</td>
          </tr>
          {% endif %}
        </table>
    </div>

  </div>

  <div class="addr-section">

    <!-- Consignee -->
    <div class="addr-cell">
      {% set mode_value = (doc.custom_mode or dn.custom_mode or dn.mode_of_transport or "") %}
        <div class="addr-title">Consignee:</div>
        {% if mode_value|lower == "by sea" %}
          <b>Z To Order</b><br>
          N/A
        {% else %}
          <b>{{ ns.short_name }}</b><br>
          N/A
        {% endif %}
    </div>

    <!-- Buyer -->
    <div class="addr-cell">
      <div class="addr-title">Buyer(If Other Than Consignee):</div>
        <div class="addr-name">
          {% if cust_address and cust_address.address_title %}
            {{ cust_address.address_title }}
          {% else %}
            {{ dn.customer_name or (customer.customer_name if customer else "") }}
          {% endif %}
        </div>
        {{ cust_address.address_line1 if cust_address and cust_address.address_line1 else "" }}{% if cust_address and cust_address.address_line1 %}<br>{% endif %}
        {{ cust_address.address_line2 if cust_address and cust_address.address_line2 else "" }}{% if cust_address and cust_address.address_line2 %}<br>{% endif %}
        {% if cust_address and (cust_address.city or cust_address.pincode) %}
          {{ cust_address.city if cust_address.city else "" }}{% if cust_address.city and cust_address.pincode %}, {% endif %}{{ cust_address.pincode if cust_address.pincode else "" }}<br>
        {% endif %}
        {{ cust_address.state if cust_address and cust_address.state else "" }}{% if cust_address and cust_address.state %}<br>{% endif %}
        {{ cust_address.country if cust_address and cust_address.country else "" }}
    </div>

    <!-- Third Party -->
    <div class="addr-cell">
      <div class="addr-title">Third Party</div>
      <div class="addr-name">
          {% if shipping_address and shipping_address.address_title %}
            {{ shipping_address.address_title }}
          {% else %}
            {{ dn.customer_name or (customer.customer_name if customer else "") }}
          {% endif %}
        </div>
      {% if shipping_address %}
        {{ shipping_address.address_line1 if shipping_address.address_line1 else "" }}{% if shipping_address.address_line1 %}<br>{% endif %}
        {{ shipping_address.address_line2 if shipping_address.address_line2 else "" }}{% if shipping_address.address_line2 %}<br>{% endif %}
        {% if shipping_address.city or shipping_address.pincode %}
          {{ shipping_address.city if shipping_address.city else "" }}{% if shipping_address.city and shipping_address.pincode %}, {% endif %}{{ shipping_address.pincode if shipping_address.pincode else "" }}<br>
        {% endif %}
        {{ shipping_address.state if shipping_address.state else "" }}{% if shipping_address.state %}<br>{% endif %}
        {{ shipping_address.country if shipping_address.country else "" }}
      {% elif shipping_address_text %}
        {{ shipping_address_text }}
      {% endif %}
    </div>

    <!-- Shipping Details -->
    <div class="addr-cell">
      <div class="addr-title">Shipping Details:</div>
      <table class="ship-table">
          <tr>
            <td>Mode</td>
            <td>: {{ doc.custom_mode or dn.custom_mode or dn.mode_of_transport }}</td>
          </tr>
          <tr>
            <td>Loading Port</td>
            <td>: {{ doc.custom_loading_port or dn.custom_loading_port }}</td>
          </tr>
          <tr>
            <td>Discharge Point</td>
            <td>: {{ dn.custom_discharge_port or "" }}</td>
          </tr>
          <tr>
            <td>Final Destination</td>
            <td>: {{ doc.custom_final_destination or dn.custom_final_destination }}</td>
          </tr>
          <tr>
            <td>Incoterms</td>
            <td>: {{ dn.incoterm or "" }}{% if dn.named_place %} - {{ dn.named_place }}{% endif %}</td>
          </tr>
          <tr>
            <td>Payment Terms</td>
            <td>: {{ so.payment_terms_template if so and so.payment_terms_template else "" }}</td>
          </tr>
        </table>
    </div>

  </div>

  <table class="items-table">
    <col class="c-box">
    <col class="c-cust">
    <col class="c-gmei">
    <col class="c-desc">
    <col class="c-qty">
    <col class="c-tqty">
    <col class="c-uwt">
    <col class="c-nwt">
    <col class="c-gwt">
    <col class="c-l">
    <col class="c-w">
    <col class="c-h">
    <col class="c-cbf">
    <col class="c-cbm">
    <col class="c-boxtype">

    <thead>
      <tr>
        <th>Box</th>
        <th>Customer Part No</th>
        <th>GMEI Part</th>
        <th>Item Description</th>
        <th>Qty.<br>(No./Set)</th>
        <th>Total Qty.<br>(No./Set)</th>
        <th>Unit Wt.<br>(Kg.)</th>
        <th>Net Wt.<br>(Kg.)</th>
        <th>Gross Wt.<br>(Kg.)</th>
        <th>L(In)</th>
        <th>W(In)</th>
        <th>H(In)</th>
        <th>Cubic<br>Feet</th>
        <th>Cubic<br>Meter</th>
        <th>Box Type</th>
      </tr>
    </thead>

    <tbody>
      {%- set box_num = namespace(val=0) -%}
      {%- for box_name, group_items in grouped -%}
      {%- set group_list = group_items | list -%}
      {%- set box_num.val = box_num.val + 1 -%}

      {# Pre-calculate box-level dimension values (first non-zero wins) #}
      {%- set grp = namespace(gross=0, length=0, width=0, height=0, cbf=0, cbm=0) -%}
      {%- for gi in group_list -%}
          {%- set current_gross = (gi.custom__gross_weight or 0) | float -%}
          {%- if grp.gross == 0 and current_gross > 0 -%}
              {%- set grp.gross = current_gross -%}
          {%- endif -%}
          {%- if grp.length == 0 and ((gi.custom_length or 0) | float) > 0 -%}
              {%- set grp.length = (gi.custom_length or 0) | float -%}
          {%- endif -%}
          {%- if grp.width == 0 and ((gi.custom_width or 0) | float) > 0 -%}
              {%- set grp.width = (gi.custom_width or 0) | float -%}
          {%- endif -%}
          {%- if grp.height == 0 and ((gi.custom_height or 0) | float) > 0 -%}
              {%- set grp.height = (gi.custom_height or 0) | float -%}
          {%- endif -%}
          {%- if grp.cbf == 0 and ((gi.custom_cubic_feet or 0) | float) > 0 -%}
              {%- set grp.cbf = (gi.custom_cubic_feet or 0) | float -%}
          {%- endif -%}
          {%- if grp.cbm == 0 and ((gi.custom_cubic_meter or 0) | float) > 0 -%}
              {%- set grp.cbm = (gi.custom_cubic_meter or 0) | float -%}
          {%- endif -%}
      {%- endfor -%}

      {# Pre-calculate total rendered rows in this box:
         each parent item = 1 row + its subitem count rows #}
      {%- set row_count = namespace(total=0) -%}
      {%- for gi in group_list -%}
          {%- set gi_subs = doc.custom_sub_items
              | selectattr("parent_row_uid", "equalto", gi.custom_row_uid)
              | list
              if gi.custom_row_uid else [] -%}
          {%- set row_count.total = row_count.total + 1 + (gi_subs | length) -%}
      {%- endfor -%}

      {%- for item in group_list -%}

      {%- set item_subs = doc.custom_sub_items
          | selectattr("parent_row_uid", "equalto", item.custom_row_uid)
          | list
          if item.custom_row_uid else [] -%}

      {%- set qty     = (item.qty or 0) | float -%}
      {%- set unit_wt = (item.custom_unit_weight or 0) | float -%}
      {%- set net     = qty * unit_wt -%}

      {# Accumulate totals from parent/standalone items only #}
      {%- set ns.total_qty        = ns.total_qty + qty -%}
      {%- set ns.total_net_weight = ns.total_net_weight + net -%}
      {%- if loop.first -%}
          {%- set ns.total_gross_weight = ns.total_gross_weight + grp.gross -%}
          {%- set ns.total_cbf          = ns.total_cbf + grp.cbf -%}
          {%- set ns.total_cbm          = ns.total_cbm + grp.cbm -%}
      {%- endif -%}

      {# PARENT / STANDALONE ROW #}
      <tr>
        {%- if loop.first -%}
        <td class="box-cell" rowspan="{{ row_count.total }}">
          {{ "%02d/%02d"|format(box_num.val, total_boxes) }}
        </td>
        {%- endif -%}

        <td class="tc">
          {%- set item_doc = frappe.get_cached_doc("Item", item.item_code) -%}
          {%- set ns_cp = namespace(val="") -%}
          {%- for ci in item_doc.customer_items -%}
            {%- if ci.customer_name == dn.customer and ci.ref_code -%}
              {%- set ns_cp.val = ci.ref_code -%}
            {%- endif -%}
          {%- endfor -%}
          {{ ns_cp.val }}
        </td>

        <td class="tc">{{ item.item_code }}</td>
        <td>{{ item.description or item.item_name }}</td>
        <td class="tc">{{ qty | int }}</td>
        <td class="tc">{{ qty | int }}</td>
        <td class="tc">{{ "%.3f"|format(unit_wt) }}</td>
        <td class="tc">{{ "%.3f"|format(net) }}</td>

        {%- if loop.first -%}
        <td class="tc" rowspan="{{ row_count.total }}">{{ "%.2f"|format(grp.gross) }}</td>
        <td class="tc" rowspan="{{ row_count.total }}">{{ "%.2f"|format(grp.length) }}</td>
        <td class="tc" rowspan="{{ row_count.total }}">{{ "%.2f"|format(grp.width) }}</td>
        <td class="tc" rowspan="{{ row_count.total }}">{{ "%.2f"|format(grp.height) }}</td>
        <td class="tc" rowspan="{{ row_count.total }}">{{ "%.2f"|format(grp.cbf) }}</td>
        <td class="tc" rowspan="{{ row_count.total }}">{{ "%.2f"|format(grp.cbm) }}</td>
        <td class="tc" rowspan="{{ row_count.total }}">{{ item.custom_box_type or "" }}</td>
        {%- endif -%}
      </tr>

      {# SUBITEM ROWS #}
      {%- for si in item_subs -%}
      {%- set si_qty     = (si.qty or 0) | float -%}
      {%- set si_unit_wt = (si.custom_unit_weight or 0) | float -%}
      {%- set si_net     = (si.custom_net_weight if si.custom_net_weight else si_qty * si_unit_wt) | float -%}
      <tr class="subitem-row">
        <td class="tc"></td>
        <td class="tc">{{ si.sub_item_code }}</td>
        <td>{{ si.sub_description or si.sub_item_name or "" }}</td>
        <td class="tc">{{ si_qty | int }}</td>
        <td class="tc"></td>
        <td class="tc">{{ "%.3f"|format(si_unit_wt) }}</td>
        <td class="tc">{{ "%.3f"|format(si_net) }}</td>
      </tr>
      {%- endfor -%}

      {%- endfor -%}
      {%- endfor -%}

      <tr class="total-row">
        <td colspan="4">Total</td>
        <td>{{ "%.0f"|format(ns.total_qty|float) }}</td>
        <td>{{ "%.0f"|format(ns.total_qty|float) }}</td>
        <td>—</td>
        <td>{{ "%.3f"|format(ns.total_net_weight|float) }}</td>
        <td>{{ "%.2f"|format(ns.total_gross_weight|float) }}</td>
        <td colspan="3">—</td>
        <td>{{ "%.2f"|format(ns.total_cbf|float) }}</td>
        <td>{{ "%.2f"|format(ns.total_cbm|float) }}</td>
        <td>—</td>
      </tr>

    </tbody>

  </table>

  <div class="pl-footer">
    <div class="pl-footer-left">
      I certify the above to be true and correct.
    </div>

    <div class="pl-footer-right">
      <div class="sig-line">
        For Global Mining Equipments
      </div>
    </div>
  </div>

</div>"""


def create_print_format():
    import frappe

    name = PRINT_FORMAT_NAME

    if frappe.db.exists("Print Format", name):
        pf = frappe.get_doc("Print Format", name)
        pf.html = HTML
        pf.save(ignore_permissions=True)
        frappe.db.commit()
        print(f"Updated existing print format: {name!r}")
    else:
        pf = frappe.get_doc({
            "doctype": "Print Format",
            "name": name,
            "doc_type": "Packing Slip",
            "module": "Stock",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "disabled": 0,
            "pdf_generator": "wkhtmltopdf",
            "html": HTML,
        })
        pf.insert(ignore_permissions=True)
        frappe.db.commit()
        print(f"Created new print format: {name!r}")
