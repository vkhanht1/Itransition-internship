import os
import re
import pandas as pd
import numpy as np

stores = ['STORE1', 'STORE2', 'STORE3', 'STORE4', 'STORE5']

def parse_books_yaml(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    books = []
    current_book = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('- :id:'):
            if current_book:
                books.append(current_book)
            current_book = {}
            try:
                current_book['id'] = int(line.split(':id:')[1].strip())
            except:
                current_book['id'] = line.split(':id:')[1].strip()
        elif line.startswith(':title:'):
            current_book['title'] = line.split(':title:')[1].strip().strip('"').strip("'")
        elif line.startswith(':author:'):
            current_book['author'] = line.split(':author:')[1].strip().strip('"').strip("'")
        elif line.startswith(':genre:'):
            current_book['genre'] = line.split(':genre:')[1].strip().strip('"').strip("'")
        elif line.startswith(':publisher:'):
            pub = line.split(':publisher:')[1].strip().strip('"').strip("'")
            current_book['publisher'] = 'Unknown' if pub in ['', 'NULL', 'null', 'None'] else pub
        elif line.startswith(':year:'):
            val = line.split(':year:')[1].strip().strip('"').strip("'")
            if not val or not val.isdigit():
                current_book['year'] = None
            else:
                current_book['year'] = int(val)
    if current_book:
        books.append(current_book)
        
    df = pd.DataFrame(books)
    return df

def clean_data_and_save():
    for store in stores:
        store_dir = store
        print(f"\n================ Processing {store} ================")
        
        books_path = os.path.join(store_dir, 'books.yaml')
        if os.path.exists(books_path):
            books_df = parse_books_yaml(books_path)
            missing_years = books_df['year'].isnull().sum()
            print(f"[Books] Total records: {len(books_df)} | Missing/Invalid years: {missing_years}")
        else:
            books_df = pd.DataFrame()
            print(f"[Books] File not found: {books_path}")
        
        users_path = os.path.join(store_dir, 'users.csv')
        if os.path.exists(users_path):
            try:
                users_df = pd.read_csv(users_path)
                for col in users_df.select_dtypes(include=['object']).columns:
                    users_df[col] = users_df[col].astype(str).str.strip()
                print(f"[Users] Total registered customers: {len(users_df)}")
            except Exception as e:
                print(f"[Users] Error reading users.csv: {e}")
                users_df = pd.DataFrame()
        else:
            users_df = pd.DataFrame()
        
        orders_path = os.path.join(store_dir, 'orders.parquet')
        if os.path.exists(orders_path):
            try:
                orders_df = pd.read_parquet(orders_path)
                initial_orders_count = len(orders_df)
                print(f"[Orders] Raw order records count: {initial_orders_count}")
                
                if not books_df.empty and 'book_id' in orders_df.columns and 'id' in books_df.columns:
                    valid_books = set(books_df['id'])
                    invalid_book_orders = (~orders_df['book_id'].isin(valid_books)).sum()
                    print(f"[Integrity Check] Orders with invalid book_id: {invalid_book_orders}")
                    orders_df = orders_df[orders_df['book_id'].isin(valid_books)]

                price_col = 'paid_price' if 'paid_price' in orders_df.columns else ('price' if 'price' in orders_df.columns else None)
                if price_col:
                    q_high = orders_df[price_col].quantile(0.99)
                    q_low = orders_df[price_col].quantile(0.001)
                    
                    spikes_count = (orders_df[price_col] > q_high).sum()
                    orders_df = orders_df[(orders_df[price_col] <= q_high) & (orders_df[price_col] >= q_low)]
                    print(f"[Spike Cleaner] Removed {spikes_count} abnormal spike price records (Threshold > {q_high:.2f})")
                
                orders_df.to_parquet(orders_path, index=False)
                print(f"[Save Success] Cleaned {store} orders saved. Final record count: {len(orders_df)}")

            except Exception as e:
                print(f"[Orders] Error processing orders.parquet: {e}")
        else:
            print(f"[Orders] File not found: {orders_path}")

if __name__ == "__main__":
    clean_data_and_save()