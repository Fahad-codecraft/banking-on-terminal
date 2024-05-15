from appwrite.client import Client
from appwrite.services import databases, account, users
from appwrite.id import ID
from dotenv import load_dotenv
import os
from appwrite.query import Query
import random
# Load environment variables from .env file
load_dotenv()

# Initialize Appwrite client
client = Client()
client.set_endpoint(os.getenv('APPWRITE_ENDPOINT'))
client.set_project(os.getenv('APPWRITE_PROJECT'))
client.set_key(os.getenv('APPWRITE_KEY'))

# Initialize Appwrite database, account, and users services
db = databases.Databases(client)
acc = account.Account(client)
user = users.Users(client)

# Get environment variables
db_id = os.getenv('APPWRITE_DATABASE_ID')
collec_id = os.getenv('APPWRITE_USER_COLLECTION_ID')
bank_collec_id = os.getenv('APPWRITE_BANK_COLLECTION_ID')
money_collec = os.getenv('APPWRITE_MONEY_COLLECTION_ID')
transaction_collec = os.getenv('APPWRITE_TRANSACTION_COLLECTION_ID')
loan_collec = os.getenv('APPWRITE_LOAN_COLLECTION_ID')

# Function to handle user login
def login(email, password):
    # Create a session using email and password
    session = acc.create_email_password_session(email, password)
    # Get user information using userId from session
    user = getUser(session['userId']) 
    return user

# Function to get user information by userId
def getUser(userId):
    try:
        user = db.list_documents(   
            database_id=db_id,
            collection_id=collec_id,
            queries=[Query.equal('userId', [userId])]
        )
        return user['documents'][0] 
    except Exception as e:
        print("Error occurred:", e)

# Function to create a new account
def newAccount(data):
    email, firstName, lastName = data['email'], data['firstName'], data['lastName']
    password = data['password']
    # Create a new account using email and password
    newacc = acc.create(
        user_id=ID.unique(),
        email=email,
        password=password,
        name=firstName + ' ' + lastName
    )

    # Create a document in the user collection with user information
    data_without_password = {key: value for key, value in data.items() if key != 'password'}
    newUser = db.create_document(
        database_id=db_id,
        collection_id=collec_id,
        document_id=ID.unique(),
        data={
            **data_without_password,
            'userId': newacc['$id'] 
        }
    )
    return newUser

# Function to generate a random account number
def generate_accountId():
    while True:
        accountId = ''.join([str(random.randint(0, 9)) for _ in range(12)])  # Adjust length as needed
        if not is_accountId_exists(accountId):
            return accountId

# Function to check if an account number already exists
def is_accountId_exists(accountId):
    existing_accounts = db.list_documents(
        database_id=db_id,
        collection_id=bank_collec_id,
        queries=[Query.equal('accountId', accountId)]
    )
    return len(existing_accounts['documents']) > 0 

# Function to add a bank account for a user
def addBankAccount(userId):
    accountId = generate_accountId()

    # Create bank account document
    bankAccount = db.create_document(
        database_id=db_id,
        collection_id=bank_collec_id,
        document_id=ID.unique(),
        data={
            'userId': userId,
            'accountId': accountId
        }
    )

    # Create money account document
    id = bankAccount['$id']
    moneyacc = db.create_document(
        database_id=db_id,
        collection_id=money_collec,
        document_id=ID.unique(),
        data={
            'money': '0',
            'accountId': id
        }
    )
    return bankAccount, moneyacc

# Function to get user information by email
def getUserByEmail(email):
    try:
        user = db.list_documents(
            database_id=db_id,
            collection_id=collec_id,
            queries=[Query.equal('email', email)]
        )
        if len(user['documents']) > 0: 
            return user['documents'][0] 
        else:
            return None
    except Exception as e:
        print("Error occurred:", e)

# Function to get account balance by accountId
def getAccountBalance(accountId):
    try:
        response = db.list_documents(
            database_id=db_id,
            collection_id=money_collec,
            queries=[Query.equal('accountId', accountId)]
        )
        return float(response['documents'][0]['money'])
    except Exception as e:
        print("Error occurred:", e)

# Function to update account balance
def updateAccountBalance(accountId, new_balance):
    try:
        res = db.list_documents(
            database_id=db_id,
            collection_id=money_collec,
            queries=[Query.equal('accountId', accountId)]
        )

        # Update document with new balance
        db.update_document(
            database_id=db_id,
            collection_id=money_collec,
            document_id=res['documents'][0]['$id'],
            data={
                'money': str(new_balance)
            }
        )
    except Exception as e:
        print("Error occurred:", e)

# Function to create a transaction
def createTransaction(data):
    try:
        trans = db.create_document(
            database_id=db_id,
            collection_id=transaction_collec,
            document_id=ID.unique(),
            data=data
        )
        return trans
    except Exception as e:
        print("Error occurred:", e)

# Function to transfer money between accounts
def transferMoney(sender_email,sender_account, recipient_email,recipient_account, amount):
    sender = getUserByEmail(sender_email)
    if not sender:
        print("Sender email not found.")
        return
    
    # Get recipient's information
    recipient = getUserByEmail(recipient_email)
    if not recipient:
        print("Recipient email not found.")
        return
    
    # Get sender's bank account
    sender_account = getBankAccountId(sender['$id']) 
    if not sender_account:
        print("Sender does not have a bank account.")
        return

    # Get recipient's bank account
    recipient_account = getBankAccountId(recipient['$id'])
    if not recipient_account:
        print("Recipient does not have a bank account.")
        return

    # Validate sender's balance
    sender_balance = getAccountBalance(sender_account['$id']) 
    if sender_balance < amount:
        print("Insufficient funds.")
        return
    
    recipient_balance = getAccountBalance(recipient_account['$id']) 

    data = {
        'senderEmail': sender_email,
        'receiverEmail': recipient_email,
        'senderAccount': sender_account['accountId'],
        'receiverAccount': recipient_account['accountId'],
        'amount': str(amount),
        'category': 'Online Transfer'
    }

    # Create transaction record
    createTransaction(data)

    # Deduct amount from sender's account
    updateAccountBalance(sender_account['$id'], sender_balance - amount) 

    # Add amount to recipient's account
    updateAccountBalance(recipient_account['$id'], recipient_balance + amount) 

    print("Transaction successful.")

# Function to get bank account id by userId
def getBankAccountId(userId):
    try:
        response = db.list_documents(
            database_id=db_id,
            collection_id=bank_collec_id,
            queries=[Query.equal('userId', userId)]
        )
        if len(response['documents']) > 0:
            return response['documents'][0]
        else:
            return None
    except Exception as e:
        print("Error occurred:", e)

def requestLoan(data):
    try:
        loan = db.create_document(
            database_id=db_id,
            collection_id=loan_collec,
            document_id=ID.unique(),
            data=data
        )
        return loan
    except Exception as e:
        print("Error occurred:", e) 

def hasActiveLoan(accountId):
    try:
        response = db.list_documents(
            database_id=db_id,
            collection_id=loan_collec,
            queries=[
                Query.equal('accountId', accountId),
                Query.equal('remainingAmount', '0')
            ]
        )
        return len(response['documents']) > 0
    except Exception as e:
        print("Error occurred:", e)

# Function to repay the loan
def listActiveLoans(userId):
    try:
        response = db.list_documents(
            database_id=db_id,
            collection_id=loan_collec,
            queries=[
                Query.equal('accountId', userId),
                Query.not_equal('remainingAmount', '0.0')
            ]
        )
        loans = response['documents']
        return loans
    except Exception as e:
        print("Error occurred:", e)

# Function to repay a specific loan chosen by the user
def repayLoan(email):
    try:
        user = getUserByEmail(email)
        bank_account = getBankAccountId(user['$id'])
        accountId = bank_account['$id']
        loans = listActiveLoans(accountId)
        if loans:
            print("Active Loans:")
            for i, loan in enumerate(loans):
                print(f"{i+1}. Loan Amount: {loan.get('principalAmount')} - Remaining Amount: {loan.get('remainingAmount')}")
            loan_choice = int(input("Enter the number of the loan you want to repay: "))
            if 1 <= loan_choice <= len(loans):
                loan_to_repay = loans[loan_choice - 1]
                remainingAmount = float(loan_to_repay['remainingAmount'])
                print("Your remaining loan amount is:", remainingAmount)
                repayment = float(input("Enter the amount you want to repay: "))
                if repayment > remainingAmount:
                    print("You cannot repay more than your remaining loan amount.")
                else:
                    RemainAmount = remainingAmount - repayment
                    newRemainingAmount = round(RemainAmount, 2)
                    
                    db.update_document(
                        database_id=db_id,
                        collection_id=loan_collec,
                        document_id=loan_to_repay['$id'],
                        data={'remainingAmount': str(newRemainingAmount)}
                    )
                    transaction_data = {
                        'senderEmail': email,
                        'receiverEmail': "loan@bank.com",
                        'senderAccount': bank_account['accountId'],
                        'receiverAccount': 'bank',
                        'amount': str(repayment),
                        'category': 'Loan Repayment'
                    }
                    createTransaction(transaction_data)
                    print("Loan repayment successful.")
            else:
                print("Invalid loan choice.")
        else:
            print("No active loans found.")
    except Exception as e:
        print("Error occurred:", e)

def getLoans(email):
    user = getUserByEmail(email)
    bank_account = getBankAccountId(user['$id'])
    accountId = bank_account['$id']
    loans = listActiveLoans(accountId)
    if loans:
        print("Active Loans:")
        for i, loan in enumerate(loans):
            print(f"{i+1}. Loan Amount: {loan.get('principalAmount')} - Remaining Amount: {loan.get('remainingAmount')}")
    else:
        print('No active loans found.')


def checkBalanceAction(email):
    print('Checking balance...')
    user = getUserByEmail(email)
    bank_account = getBankAccountId(user['$id'])
    account_balance = getAccountBalance(bank_account['$id'])
    print("Your account balance is: ", account_balance)

def moneyTransferAction(email):
    recipient_email = input("Enter recipient's email: ")
    recipient_account = input("Enter recipient's account number: ")
    print("Transferring money...")
    amount = float(input("Enter amount: "))
    useri = getUserByEmail(email)
    sender = getBankAccountId(useri['$id'])
    sender_account = sender['accountId']
    transferMoney(email, sender_account, recipient_email, recipient_account, amount)

def depositCashAction(email):
    amount = float(input("Enter amount to deposit: "))
    print("Depositing cash...")
    useri = getUserByEmail(email)
    bank_account = getBankAccountId(useri['$id'])
    account_balance = float(getAccountBalance(bank_account['$id']))
    updated_balance = account_balance + amount
    updateAccountBalance(bank_account['$id'], updated_balance)
    data = {
        'senderEmail': email,
        'receiverEmail': email,
        'senderAccount': bank_account['accountId'],
        'receiverAccount': bank_account['accountId'],
        'amount': str(amount),
        'category': 'Cash Deposit'
        }
    createTransaction(data)
    print("Deposit successful. Your updated balance is:", updated_balance)

def requestLoanAction(email):
    user = getUserByEmail(email)
    bank_account = getBankAccountId(user['$id'])
    accountId = bank_account['$id']
    principalAmount = float(input("Enter the principal amount: "))
    time = float(input("Enter the time you will repay loan in years: "))
    iRate = random.uniform(6.7, 9.1)
    interestRate = round(iRate, 2)
    repayAmount = principalAmount + (principalAmount * interestRate * time)/100
    remainingAmount = repayAmount
    data = {
        'principalAmount': str(principalAmount),
        'time': str(time),
        'intrestRate': str(interestRate),
        'repayAmount': str(repayAmount),
        'accountId': accountId,
        'remainingAmount': str(remainingAmount)
    }
    requestLoan(data)
    money = getAccountBalance(accountId)
    new_money = float(money) + principalAmount
    updateAccountBalance(accountId, new_money)
    tras = {
        'senderEmail': "loan@bank.com",
        'receiverEmail': email,
        'senderAccount': 'bank',
        'receiverAccount': bank_account['accountId'],
        'amount': str(principalAmount),
        'category': 'Loan'
    }
    createTransaction(tras)

def repayLoanAction(email):
    repayLoan(email)

def createAccountAction(email, firstName, lastName, password):
    data = {
        'email': email,
        'firstName': firstName,
        'lastName': lastName,
        'password': password
    }
    accc = newAccount(data)
    addBankAccount(accc['$id'])

    return accc

# Function to handle actions after user login
def loginActions():
    while True:
        try:
            email = input("Enter your email: ")
            password = input("Enter your password: ")
            user = login(email, password)
            if user:
                print("Login successful.")
                print("Welcome,", user['firstName']) # type: ignore
                while True:
                    print("What would you like to do?")
                    print("1. Check balance")
                    print("2. Transfer money")
                    print("3. Deposit cash")
                    print("4. Request Loan")
                    print("5. Repay Loan")
                    print("6. Check Loans")
                    print("7. Logout")
                    action = input("Enter your choice: ")
                    if action == '1':
                        checkBalanceAction(email)
                        input("Press Enter to continue...")
                    elif action == '2':
                        moneyTransferAction(email)
                        input("Press Enter to continue...")
                    elif action == '3':
                        depositCashAction(email)
                        input("Press Enter to continue...")
                    elif action == '4':
                        requestLoanAction(email)
                        print("Loan request successful.")
                    elif action == '5':
                        repayLoanAction(email)
                    elif action == '6':
                        getLoans(email)
                        input("Press Enter to continue...")
                    elif action == '7':
                        print("Logging out...")
                        return
                    else:
                        print("Invalid choice.")
            else:
                print("Login failed. Please check your email and password.")
        except Exception as e:
            print("Error occurred:", e)

def main():
    userAction = input("Do you have an account? (y/n): ")
    if userAction == 'y':
        print("Login to your account.")
        loginActions()
    elif userAction == 'n':
        print("Create an account.")
        firstName = input("Enter your first name: ")
        lastName = input("Enter your last name: ")
        email = input("Enter your email: ")
        password = input("Enter your password: ")
        createAccountAction(email, firstName, lastName, password)
    else:
        print("Invalid choice.")

if __name__ == '__main__':
    main()