import glob
import os
import matplotlib.pyplot as plt
import pandas as pd
import yaml

def load_and_process_all_stores(base_dir='.'):
  all_orders = []
  all_users = []
  all_books = []

  store_folders = glob.glob(os.path.join(base_dir, 'STORE*'))
  if not store_folders:
    store_folders = glob.glob('STORE*')
  if not store_folders:
    store_folders = glob.glob('task4/STORE*')

  print(
      f'DEBUG - Scanning path: {os.path.abspath(base_dir)} | Found stores:'
      f' {store_folders}'
  )

  for store_path in store_folders:
    store_name = os.path.basename(store_path)

    users_file = os.path.join(store_path, 'users.csv')
    orders_file = os.path.join(store_path, 'orders.parquet')
    books_file = os.path.join(store_path, 'books.yaml')

    if os.path.exists(users_file):
      try:
        df_u = pd.read_csv(users_file, on_bad_lines='skip')
        df_u['store'] = store_name
        all_users.append(df_u)
      except Exception as e:
        print(f'Error reading users in {store_name}: {e}')

    if os.path.exists(orders_file):
      try:
        df_o = pd.read_parquet(orders_file)

        if 'timestamp' in df_o.columns:
          s = pd.to_datetime(
              df_o['timestamp'].astype(str),
              errors='coerce',
              utc=True,
              format='mixed',
          )
          df_o['timestamp'] = s.dt.tz_localize(None)

        if 'quantity' in df_o.columns:
          df_o['quantity'] = (
              df_o['quantity']
              .astype(str)
              .str.replace(r'[^0-9.]', '', regex=True)
          )
          df_o['quantity'] = pd.to_numeric(
              df_o['quantity'], errors='coerce'
          ).fillna(0)

        if 'unit_price' in df_o.columns:
          df_o['unit_price'] = (
              df_o['unit_price']
              .astype(str)
              .str.replace(r'[^0-9.]', '', regex=True)
          )
          df_o['unit_price'] = pd.to_numeric(
              df_o['unit_price'], errors='coerce'
          ).fillna(0.0)

        df_o['store'] = store_name
        all_orders.append(df_o)
      except Exception as e:
        print(f'Error reading orders in {store_name}: {e}')

    if os.path.exists(books_file):
      try:
        with open(books_file, 'r', encoding='utf-8') as f:
          books_data = yaml.safe_load(f)
          if isinstance(books_data, list):
            df_b = pd.DataFrame(books_data)
            for col in df_b.columns:
              if 'year' in col.lower():
                df_b[col] = pd.to_numeric(df_b[col], errors='coerce')
                df_b[col] = df_b[col].apply(
                    lambda x: None if pd.isna(x) or x < 1800 else int(x)
                )
            df_b['store'] = store_name
            all_books.append(df_b)
      except Exception as e:
        print(f'Error reading books in {store_name}: {e}')

  combined_orders = (
      pd.concat(all_orders, ignore_index=True) if all_orders else pd.DataFrame()
  )
  combined_users = (
      pd.concat(all_users, ignore_index=True) if all_users else pd.DataFrame()
  )
  combined_books = (
      pd.concat(all_books, ignore_index=True) if all_books else pd.DataFrame()
  )

  if (
      not combined_orders.empty
      and 'quantity' in combined_orders.columns
      and 'unit_price' in combined_orders.columns
  ):
    combined_orders['paid_price'] = (
        combined_orders['quantity'] * combined_orders['unit_price'] * 1.2
    )

  if not combined_orders.empty and 'timestamp' in combined_orders.columns:
    combined_orders['date'] = pd.to_datetime(
        combined_orders['timestamp']
    ).dt.strftime('%Y-%m-%d')

  return combined_orders, combined_users, combined_books
