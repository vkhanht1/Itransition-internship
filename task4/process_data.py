import glob
import os
import pandas as pd
import streamlit as st
import yaml


@st.cache_data
def load_store_data(store_path):
  store_name = os.path.basename(store_path)
  users_file = os.path.join(store_path, 'users.csv')
  orders_file = os.path.join(store_path, 'orders.parquet')
  books_file = os.path.join(store_path, 'books.yaml')

  df_u = pd.DataFrame()
  df_o = pd.DataFrame()
  df_b = pd.DataFrame()

  if os.path.exists(users_file):
    try:
      df_u = pd.read_csv(users_file, on_bad_lines='skip')
      df_u['store'] = store_name
    except Exception:
      pass

  if os.path.exists(orders_file):
    try:
      df_o = pd.read_parquet(orders_file)
      if 'timestamp' in df_o.columns:
        s = pd.to_datetime(
            df_o['timestamp'].astype(str), errors='coerce', utc=True
        )
        df_o['timestamp'] = s.dt.tz_localize(None)
        df_o = df_o.dropna(subset=['timestamp'])
        df_o['date'] = df_o['timestamp'].dt.strftime('%Y-%m-%d')

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

      df_o = df_o[
          (df_o['quantity'] > 0)
          & (df_o['quantity'] < 10000)
          & (df_o['unit_price'] > 0)
          & (df_o['unit_price'] < 100000)
      ]

      df_o['paid_price'] = df_o['quantity'] * df_o['unit_price'] * 1.2
      df_o['store'] = store_name
    except Exception:
      pass

  if os.path.exists(books_file):
    try:
      with open(books_file, 'r', encoding='utf-8') as f:
        books_data = yaml.safe_load(f)
        if isinstance(books_data, list):
          df_b = pd.DataFrame(books_data)
          for col in df_b.columns:
            if 'author' in col.lower():
              df_b.rename(columns={col: 'authors'}, inplace=True)
              break
          df_b['store'] = store_name
    except Exception:
      pass

  return df_u, df_o, df_b


@st.cache_data
def load_all_stores(base_dir='.'):
  store_folders = sorted(glob.glob(os.path.join(base_dir, 'STORE*')))
  if not store_folders:
    store_folders = sorted(glob.glob('STORE*'))
  if not store_folders:
    store_folders = sorted(glob.glob('task4/STORE*'))

  stores_dict = {}
  for store_path in store_folders:
    store_name = os.path.basename(store_path)
    df_u, df_o, df_b = load_store_data(store_path)
    stores_dict[store_name] = {'users': df_u, 'orders': df_o, 'books': df_b}
  return stores_dict


def compute_store_analytics(users_df, orders_df, books_df):
  if not orders_df.empty and 'date' in orders_df.columns:
    daily_rev = orders_df.groupby('date')['paid_price'].sum().reset_index()
    top_5 = daily_rev.sort_values(by='paid_price', ascending=False).head(5)
  else:
    top_5 = pd.DataFrame(columns=['date', 'paid_price'])

  unique_users_count = 0
  best_buyer_info = {'aliases': [], 'spending': 0.0}

  if not users_df.empty:
    u_df = users_df.copy()
    for col in ['name', 'address', 'phone', 'email']:
      if col in u_df.columns:
        u_df[col] = u_df[col].astype(str).str.strip().str.lower()
      else:
        u_df[col] = ''

    records = u_df.to_dict('records')
    ids = [r.get('id', idx) for idx, r in enumerate(records)]

    adjacency = {uid: [] for uid in ids}
    fields = ['name', 'address', 'phone', 'email']

    for i in range(len(records)):
      for j in range(i + 1, len(records)):
        r1, r2 = records[i], records[j]
        matches = sum(1 for f in fields if r1[f] == r2[f])
        if matches >= 3:
          id1, id2 = ids[i], ids[j]
          adjacency[id1].append(id2)
          adjacency[id2].append(id1)

    visited = set()
    components = []
    for uid in ids:
      if uid not in visited:
        comp = []
        stack = [uid]
        visited.add(uid)
        while stack:
          curr = stack.pop()
          comp.append(curr)
          for neighbor in adjacency.get(curr, []):
            if neighbor not in visited:
              visited.add(neighbor)
              stack.append(neighbor)
        components.append(comp)

    unique_users_count = len(components)

    if not orders_df.empty and 'user_id' in orders_df.columns:
      cluster_spending = {}
      for comp in components:
        rev = orders_df[orders_df['user_id'].isin(comp)]['paid_price'].sum()
        cluster_spending[tuple(comp)] = rev

      if cluster_spending:
        best_cluster = max(cluster_spending, key=cluster_spending.get)
        best_buyer_info = {
            'aliases': list(best_cluster),
            'spending': cluster_spending[best_cluster],
        }

  unique_author_sets_count = 0
  most_popular_author = 'N/A'

  if not books_df.empty and 'authors' in books_df.columns:
    books_df['authors_str'] = (
        books_df['authors'].astype(str).str.strip().str.lower()
    )
    unique_author_sets_count = books_df['authors_str'].nunique()

    author_counts = books_df['authors'].astype(str).value_counts()
    if not author_counts.empty:
      most_popular_author = str(author_counts.index[0])

  return {
      'top_5_days': top_5,
      'unique_users_count': unique_users_count,
      'unique_author_sets_count': unique_author_sets_count,
      'most_popular_author': most_popular_author,
      'best_buyer': best_buyer_info,
  }
