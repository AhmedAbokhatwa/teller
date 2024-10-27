
import frappe
from frappe import _
from erpnext.accounts.utils import get_account_balances
from erpnext.accounts.utils import get_balance_on
from frappe.utils import today
@frappe.whitelist()
def get():    
    company = frappe.defaults.get_user_default("Company")
    account = "1100-1600 - Current Assets - AE"
    balances = get_balance_on(account= account, date =today(), company=company)
    print("balance",balances)
@frappe.whitelist()    
def get_dimension_with_children(doctype, dimensions):
	if isinstance(dimensions, str):
		dimensions = [dimensions]

	all_dimensions = []

	for dimension in dimensions:
		lft, rgt = frappe.db.get_value(doctype, dimension, ["lft", "rgt"])
		children = frappe.get_all(doctype, filters={"lft": [">=", lft], "rgt": ["<=", rgt]}, order_by="lft")
		all_dimensions += [c.name for c in children]

	return all_dimensions  
  
@frappe.whitelist()
def get2(name):
    data = frappe.db.sql(
		"""SELECT is_group,lft, rgt, name, account_currency,parent_account
FROM tabAccount
WHERE lft BETWEEN (SELECT lft FROM tabAccount WHERE name = %s)
               AND (SELECT rgt FROM tabAccount WHERE name = %s)
  AND name != %s
  AND is_group = 0
ORDER BY lft;""",(name,name,name),
		
		as_dict=1,
	)
    # for root in data:
    return data	

@frappe.whitelist()
def get_branches(name):
    data = frappe.db.sql(
		"""SELECT is_group,lft, rgt, name, account_currency,parent_account
FROM tabAccount
WHERE lft BETWEEN (SELECT lft FROM tabAccount WHERE name = %s)
               AND (SELECT rgt FROM tabAccount WHERE name = %s)
  AND name != %s
    AND is_group = 1
    AND parent_account = '1100 - خزن الفروع - AE'
ORDER BY lft;""",(name,name,name),
		
		as_dict=1,
	)
    # for root in data:
    return data	


@frappe.whitelist()
def get_branch(name):
    # Fetch the hierarchical data
    data = frappe.db.sql(
        """SELECT is_group, lft, rgt, name, account_currency, parent_account
           FROM tabAccount
           WHERE lft BETWEEN (SELECT lft FROM tabAccount WHERE name = %s)
               AND (SELECT rgt FROM tabAccount WHERE name = %s)
             AND name != %s
            
             
           ORDER BY lft;""",
        (name, name, name),
        as_dict=True
    )
    
    # Identify the parent account for the given branch
    parent_account_name = name
    
    # Process the data to update parent_account field based on hierarchy
    processed_data = []
    for row in data:
    #     if row.get('parent_account') != parent_account_name:
    #         row['parent_account'] = parent_account_name
    #     processed_data.append(row)
    
    # return processed_data
        return data
    
    
@frappe.whitelist()
def get_acc_gl (name):
    
    # Fetch the hierarchical data
    data = frappe.db.sql("""
    SELECT is_group, lft, rgt, acc.name, acc.account_currency, parent_account

                FROM
             
                    `tabAccount` acc
                where parent_account = %s
            
                """,name,as_dict=True)
    return get_brach_both_treasures(data)
    # return data
    
@frappe.whitelist()
def get_brach_both_treasures(data):
    result = {
        'data1': [],
        'data2': []
    }
    for record in data:
        main_branch = [record.name for record in data ]
        placeholders = ', '.join(['%s'] * len(main_branch))
        # return main_branch    
        if record.is_group == 0:
            # print("RECCCORDDD",record.is_group == 0,record)
           
            sql1 = """
                SELECT
                    `tabAccount`.name AS branch,
                    ge.account,
                    `tabAccount`.parent_account,
                    ge.account_currency,
                    SUM(ge.debit_in_account_currency) - SUM(ge.credit_in_account_currency) AS balance,
                    SUM(ge.debit) - SUM(ge.credit) AS balance2
                FROM
                    `tabGL Entry` ge
                INNER JOIN
                    `tabAccount`
                ON `tabAccount`.name = ge.account
                WHERE
                    `tabAccount`.parent_account = %(account_name)s
                GROUP BY
                    ge.account, ge.account_currency
            """
            result['data1'] = frappe.db.sql(sql1, {"account_name": record["parent_account"]}, as_dict=True)

        if record.is_group == 1:
            #account_names = [record.name for record in data if record.is_group]
            main_branch = [record.name for record in data ]
            # return ("mom",main_branch)
            if main_branch:
    #             # Use `IN` clause for multiple values
                placeholders = ', '.join(['%s'] * len(main_branch))
                sql2 = f"""
                    SELECT
                        `tabAccount`.name AS branch,
                        ge.account,
                        `tabAccount`.parent_account,
                        ge.account_currency,
                        SUM(ge.debit_in_account_currency) - SUM(ge.credit_in_account_currency) AS balance,
                        SUM(ge.debit) - SUM(ge.credit) AS balance2
                    FROM
                        `tabGL Entry` ge
                    INNER JOIN
                        `tabAccount`
                    ON `tabAccount`.name = ge.account
                    WHERE
                        `tabAccount`.parent_account IN ({placeholders})
                    GROUP BY
                        ge.account, ge.account_currency
                """
                result['data2'] = frappe.db.sql(sql2, tuple(main_branch), as_dict=True)
        if record.is_group == 0:
            # print("RECCCORDDD",record.is_group == 0,record)
            sql1 = """
                SELECT
                    `tabAccount`.name AS branch,
                    ge.account,
                    `tabAccount`.parent_account,
                    ge.account_currency,
                    SUM(ge.debit_in_account_currency) - SUM(ge.credit_in_account_currency) AS balance,
                    SUM(ge.debit) - SUM(ge.credit) AS balance2
                FROM
                    `tabGL Entry` ge
                INNER JOIN
                    `tabAccount`
                ON `tabAccount`.name = ge.account
                WHERE
                    `tabAccount`.parent_account = %(account_name)s
                GROUP BY
                    ge.account, ge.account_currency
            """
            result['data1'] = frappe.db.sql(sql1, {"account_name": record["parent_account"]}, as_dict=True)
    return process_data(result)    
                
def process_data(result):
    
    # Ensure data1 and data2 are not None
    # data1 = data1 or []
    # data2 = data2 or []
    # result = data1 + data2
    # print("RESult",filters.get("branch"),result)
    # Initialize dictionaries to store totals
    totals = {}
    # for entry in result:
    currency = 'USD'

    if currency not in totals:
        totals[currency] = {'total_balance': 0.0, 'total_balance2': 0.0}
    
    #     # Add to totals
        totals[currency]['total_balance'] += result.get('balance', 0.0)
        totals[currency]['total_balance2'] += result.get('balance2', 0.0)
        

    # # Convert totals to the desired format
    # formatted_result = [{ 
    #     'branch':"branch",             
    #     'account_currency': currency, 
    #     'balance': values['total_balance'], 
    #     'balance2': values['total_balance2']
    # } for currency, values in totals.items()]

        return 
    
    # return getMYBranch(data)
    
# @frappe.whitelist()
# def getMYBranch(data):
#     result = {
#         'data1': [],
#         'data2': []
#     }

#     for record in data:
#         if record['is_group'] == 1:  # Access using dictionary keys
#             account_names = [record.name for record in data]
#             placeholders = ', '.join(['%s'] * len(account_names))
    #         sql2 = f"""
    #             SELECT
    #                 acc.name AS branch,
    #                 ge.account,
    #                 acc.parent_account,
    #                 ge.account_currency,
    #                 COALESCE(SUM(ge.debit_in_account_currency) - SUM(ge.credit_in_account_currency), 0) AS balance,
    #                 COALESCE(SUM(ge.debit) - SUM(ge.credit), 0) AS balance2
    #             FROM `tabGL Entry` ge
    #             INNER JOIN `tabAccount` acc ON acc.name = ge.account

    #             GROUP BY ge.account, ge.account_currency
    #         """
            
    #         # Fetch the GL entries for the account
    #         result['data2'] = frappe.db.sql(sql2, as_dict=True)
            

    
    #         return result

            # sql1 = """
            #     SELECT
            #         `tabAccount`.name AS branch,
            #         ge.account,
            #         `tabAccount`.parent_account,
            #         ge.account_currency,
            #         SUM(ge.debit_in_account_currency) - SUM(ge.credit_in_account_currency) AS balance,
            #         SUM(ge.debit) - SUM(ge.credit) AS balance2
            #     FROM
            #         `tabGL Entry` ge
            #     INNER JOIN
            #         `tabAccount`
            #     ON `tabAccount`.name = ge.account
            #     WHERE
            #         `tabAccount`.parent_account = %(account_name)s
            #     GROUP BY
            #         ge.account, ge.account_currency
            # """
            # result['data1'] = frappe.db.sql(sql1, {"account_name": account_name}, as_dict=True)
            # return result