import glob
import os
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
      except Exception:
        pass

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
      except Exception:
        pass

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
      except Exception:
        pass

  combined_orders = (
      pd.concat(all_orders, ignore_index=True)
      if all_orders
      else pd.DataFrame()
  )
  combined_users = (
      pd.concat(all_users, ignore_index=True)
      if all_users
      else pd.DataFrame()
  )
  combined_books = (
      pd.concat(all_books, ignore_index=True)
      if all_books
      else pd.DataFrame()
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


def compute_analytics(orders_df, users_df, books_df):
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
    ids = [
        r.get('id', i)
        for i, r in enumerate(records)
        if 'id' in r or i < len(records)
    ]
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
      if uid not visited:
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

    merged = pd.DataFrame()
    if not orders_df.empty:
      book_key_o = (
          'book_id'
          if 'book_id' in orders_df.columns
          else ('id' if 'id' in orders_df.columns else None)
      )
      book_key_b = 'id' if 'id' in books_df.columns else None
      if book_key_o and book_key_b:
        merged = pd.merge(
            orders_df,
            books_df,
            left_on=book_key_o,
            right_on=book_key_b,
            how='inner',
        )

    if not merged.empty and 'quantity' in merged.columns:
      pop_author = merged.groupby('authors')['quantity'].sum().reset_index()
      if not pop_author.empty:
        top_auth_row = pop_author.sort_values(
            by='quantity', ascending=False
        ).iloc[0]
        most_popular_author = str(top_auth_row['authors'])
    else:
      most_popular_author = (
          books_df['authors'].astype(str).value_counts().idxmax()
          if not books_df['authors'].empty
          else 'N/A'
      )

  return {
      'top_5_days': top_5,
      'unique_users_count': unique_users_count,
      'unique_author_sets_count': unique_author_sets_count,
      'most_popular_author': most_popular_author,
      'best_buyer': best_buyer_info,
  }
