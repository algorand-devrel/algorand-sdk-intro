import algokit_utils as algokit
import algosdk as algosdk
from algosdk import atomic_transaction_composer as atc
# ===== Create two accounts =====

[alice_sk, alice_addr] = algosdk.account.generate_account()
[bob_sk, bob_addr] = algosdk.account.generate_account()

print("Alice's address:", alice_addr)

    # // ===== Get information about alice from algod =====
    # const algod = algokit.getAlgoClient(algokit.getDefaultLocalNetConfig('algod'));

    # console.log("Algod verisions:", await algod.versionsCheck().do());
    # console.log("Alice's Account:", await algod.accountInformation(alice.addr).do());

# ===== Get information about Alice from algod =====
algod = algokit.get_algod_client(algokit.get_default_localnet_config('algod'))

print("Algod versions:", algod.versions().get('versions'))
print("Alice's Account:", algod.account_info(alice_addr))

# ===== Fund Alice's account =====
kmd = algokit.get_kmd_client_from_algod_client(algod)
dispenser = algokit.get_dispenser_account(algod)
alice_fund_txn = algosdk.transaction.PaymentTxn(
    sender=dispenser.address,
    sp=algod.suggested_params(),
    receiver=alice_addr,
    amt=int(10e6)
)

alice_signer = atc.AccountTransactionSigner(alice_sk)
dispenser_signer = dispenser.signer

alice_fund_atc = atc.AtomicTransactionComposer()

alice_fund_atc.add_transaction(atc.TransactionWithSigner(txn=alice_fund_txn, signer=dispenser_signer))

alice_fund_atc.execute(algod, 3)

print("Alice's Account:", algod.account_info(alice_addr))

# ===== Create the ASA. ASA === Algorand Standard Asset =====
asa_creation = algosdk.transaction.AssetConfigTxn(
    sender=alice_addr,
    total=100,
    decimals=0,
    default_frozen=False,
    sp=algod.suggested_params(),
    strict_empty_address_check=False,
)

asa_create_atc = atc.AtomicTransactionComposer()
asa_create_atc.add_transaction(atc.TransactionWithSigner(txn=asa_creation, signer=alice_signer))
create_result = asa_create_atc.execute(algod, 3)

create_txid = create_result.tx_ids[0]
confirmation = algod.pending_transaction_info(create_txid)
asset_index = confirmation.get('asset-index')

asa_transfer = algosdk.transaction.AssetTransferTxn(
    sender=alice_addr,
    receiver=bob_addr,
    index=asset_index,
    amt=1,
    sp=algod.suggested_params(),
)

transfer_atc = atc.AtomicTransactionComposer()
transfer_atc.add_transaction(atc.TransactionWithSigner(txn=asa_transfer, signer=alice_signer))

try:
    transfer_atc.execute(algod, 3)
except algosdk.error.AlgodHTTPError as e:
    print('Transfer error:', e)

# ===== Fund Bob =====
bob_fund_txn = algosdk.transaction.PaymentTxn(
    sender=dispenser.address,
    sp=algod.suggested_params(),
    receiver=bob_addr,
    amt=int(10e6)
)

bob_fund_atc = atc.AtomicTransactionComposer()
bob_fund_atc.add_transaction(atc.TransactionWithSigner(txn=bob_fund_txn, signer=dispenser_signer))
bob_fund_atc.execute(algod, 3)

# ===== Opt-in Bob to the ASA and try transfer again =====
bob_signer = atc.AccountTransactionSigner(bob_sk)

opt_in = algosdk.transaction.AssetTransferTxn(
    sender=bob_addr,
    receiver=bob_addr,
    index=asset_index,
    amt=0,
    sp=algod.suggested_params(),
)

opt_in_transfer_atc = atc.AtomicTransactionComposer()
opt_in_transfer_atc.add_transaction(atc.TransactionWithSigner(txn=opt_in, signer=bob_signer))
opt_in_transfer_atc.add_transaction(atc.TransactionWithSigner(txn=asa_transfer, signer=alice_signer))
opt_in_transfer_atc.execute(algod, 3)

print("Alice's Assets:", algod.account_asset_info(alice_addr, asset_index))
print("Bob's Assets:", algod.account_asset_info(bob_addr, asset_index))

# ==== Alice buys back ASA from Bob ====
alice_payment = algosdk.transaction.PaymentTxn(
    sender=alice_addr,
    receiver=bob_addr,
    amt=int(1e6),
    sp=algod.suggested_params(),
)

bob_transfer = algosdk.transaction.AssetTransferTxn(
    sender=bob_addr,
    receiver=alice_addr,
    index=asset_index,
    amt=1,
    sp=algod.suggested_params(),
)

buyback_atc = atc.AtomicTransactionComposer()
buyback_atc.add_transaction(atc.TransactionWithSigner(txn=alice_payment, signer=alice_signer))
buyback_atc.add_transaction(atc.TransactionWithSigner(txn=bob_transfer, signer=bob_signer))
buyback_atc.execute(algod, 3)

print("Alice's Assets:", algod.account_asset_info(alice_addr, asset_index))
print("Bob's Assets:", algod.account_asset_info(bob_addr, asset_index))
print("Bob's Min Balance:", algod.account_info(bob_addr).get('min-balance'))

# ==== Bob Close out the ASA ====

opt_out = algosdk.transaction.AssetTransferTxn(
    sender=bob_addr,
    receiver=alice_addr,
    index=asset_index,
    amt=0,
    sp=algod.suggested_params(),
    close_assets_to=alice_addr,
)

opt_out_atc = atc.AtomicTransactionComposer()
opt_out_atc.add_transaction(atc.TransactionWithSigner(txn=opt_out, signer=bob_signer))
opt_out_atc.execute(algod, 3)

print("Bob's Min Balance:", algod.account_info(bob_addr).get('min-balance'))