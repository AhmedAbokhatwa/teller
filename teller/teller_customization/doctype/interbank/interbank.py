# Copyright (c) 2024, Mohamed AbdElsabour and contributors
# For license information, please see license.txt
import frappe
from frappe.model.document import Document
from frappe import _
import json


class InterBank(Document):
    @frappe.whitelist()
    def on_submit(self):
        currency_table = self.interbank
        if not currency_table:
            frappe.throw("No bookings were created due to insufficient quantities.")
        document = frappe.new_doc("Booking Interbank")
        document.customer = self.customer
        document.type = self.transaction
        # if self.type ==
        # if self.time:
        #     document.time
        if self.date:
            document.date  
        document.user = self.user
        document.branch = self.branch
        for row in currency_table:
          requested_qty = row.qty
          currency = row.currency
          purpose = self.transaction
          data = create_queue_request(currency, purpose)
          if data:
            for record in data:
                ir_name = record.get("name")
                ir_curr_code = record.get("currency_code")
                ir_curr = record.get("currency")
                ir_qty = record.get("qty")
                ir_queue_qty = record.get("queue_qty")
                ir_rate = record.get("rate")
                if ir_queue_qty <= 0:
                    continue
                document.append("booked_currency", {
                                  "currency_code": ir_curr_code,
                                  "currency": ir_curr,
                                  "rate": ir_rate,
                                  "qty": ir_queue_qty,
                                  "interbank_reference": ir_name,
                                  "request_reference":self.name,
                                  "booking_qty": ir_queue_qty
                              })

          document.insert(ignore_permissions=True)
          frappe.msgprint("Booking Interbank document created successfully.")
        else:
            return
    def interbank_update_status(self):
          current_interbank = frappe.get_doc("InterBank", self.name)
          current_interbank.ignore_validate_update_after_submit = True
          current_interbank.db_set('status', 'Closed')
          current_interbank.save()
          
    # @frappe.whitelist()
    # def fetch_data(self):
    #     # Your logic to fetch data
    #     sql = """
    # 	   SELECT
    #         account,
    #         SUM(credit_in_account_currency) AS sum_currency_sale,
    #         SUM(debit_in_account_currency) AS sum_currency_purchase,
    #         account_currency,
    #         SUM(credit) AS sum_egy_sale,
    #         SUM(debit) AS sum_egy_purchase,
    #         posting_date
    #     FROM
    #         `tabGL Entry`
    #     WHERE
    #         account IN (SELECT name FROM `tabAccount` WHERE account_type = 'Cash')

    # 	"""

    #     sr = frappe.db.sql(sql, as_dict=True)
    #     fetched_data = sr  # Replace with actual fetched data
    #     return fetched_data

    @frappe.whitelist()
    def get_currency(self):
        doc = frappe.get_doc("InterBank", self.name)

        query = """
            SELECT
              cu.custom_currency_code,ac.account_currency, 
        SUM(gl.debit_in_account_currency) - SUM(gl.credit_in_account_currency) AS balance
            FROM `tabGL Entry` AS gl
            INNER JOIN `tabAccount` AS ac
            ON ac.name = gl.account
            INNER JOIN `tabCurrency` AS cu
            ON cu.name = ac.account_currency
            WHERE ac.custom_is_treasury = 1
            AND ac.account_currency != 'EGP'
            GROUP BY ac.account_currency;
        """
        data = frappe.db.sql(query, as_dict=True)
        doc = frappe.get_doc("InterBank", self.name)
        doc.set("interbank", [])
        for record in data:
            doc.append(
                "interbank",
                {
                    "custom_currency_code": record["custom_currency_code"],
                    "currency": record["account_currency"],
                    "remaining": record["balance"],
                    "amount": record["balance"],
                },
            )
        # doc.insert()
        doc.save()
        frappe.db.commit()
        return data

    @frappe.whitelist()
    def create_special_price_document(self):
        current_doc = frappe.get_doc("InterBank", self.name)
        interbank_list = self.interbank
        list_table = []

        if interbank_list:
            for curr in interbank_list:
                if curr.get("custom_qty") and curr.get("custom_qty") > 0:
                    list_table.append(
                        {
                            "currency": curr.get("currency"),
                            "transaction": curr.get("transaction"),
                            "custom_qty": curr.get("custom_qty"),
                            "rate": curr.get("rate"),
                        }
                    )

            print("booked_currency :", list_table)

            if list_table:  # Ensure there's data to append
                document = frappe.new_doc("Special price document")
                document.custom_transaction = current_doc.transaction
                document.custom_interbank_refrence = current_doc.name
                print("document.transaction Is :", current_doc.transaction)
                for book in list_table:
                    document.append(
                        "booked_currency",
                        {
                            "currency": book.get("currency"),
                            "transaction": book.get("transaction"),
                            "custom_qty": book.get("custom_qty"),
                            "rate": book.get("rate"),
                        },
                    )
                    for curr in interbank_list:
                        if curr.get("custom_qty"):
                            # if curr.get("remaining")> 0 or curr.get("remaining") < 0:
                            curr.set(
                                "remaining",
                                curr.get("remaining") - curr.get("custom_qty"),
                            )
                            curr.set("custom_qty", 0)
                            if curr.get("remaining") == 0:
                                return "remaining is zero so can not book now "
                                # curr.set("remaining", (curr.get("remaining")- curr.get("custom_qty")*-1))
                                # curr.set("custom_qty", 0)
                                # current_doc.save()
                                frappe.warn("remaining is zero so can not book now ")
                                break

                            # list_table.append(
                            #     {
                            #         "currency": curr.get("currency"),
                            #         "transaction": curr.get("transaction"),
                            #         "custom_qty": 0,
                            #         "rate": curr.get("rate"),
                            #         "remaining":(curr.get("remaining")- curr.get("custom_qty"))
                            #     }
                            # )

                document.insert(ignore_permissions=True)  # Save the document
                frappe.db.commit()  # Commit the transaction

                return _("Special Price Document(s) created successfully!")

        return _("No valid entries to create Special Price Document.")
@frappe.whitelist()
def create_queue_request(currency, purpose):
    sql = """
        select 
            ri.name,ri.type,
            ri.status,
            rid.currency, 
            rid.curency_code, 
            rid.qty, rid.avaliable_qty, 
            (rid.qty - rid.avaliable_qty) AS queue_qty,
            rid.creation
        from 
            `tabRequest interbank` ri 
        left join 
            `tabInterbank Request Details` rid 
        ON rid.parent = ri.name 
            where ri.status = 'In Queue'
        AND  rid.currency = %s
        AND  ri.type = %s
        ORDER BY rid.creation ASC

          """
    ri = frappe.db.sql(sql,(currency , purpose), as_dict=True)
    return ri