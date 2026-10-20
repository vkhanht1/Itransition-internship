import pandas as pd
import streamlit as st
from process_data import compute_store_analytics, load_all_stores

st.set_page_config(
    page_title='Task 4 - BI Dashboard (Per-Store)', layout='wide'
)

st.title('Business Intelligence Dashboard - Task 4 (Isolated Store Analysis)')
st.markdown(
    'Each store (`STORE1` to `STORE5`) is processed independently as'
    ' requested.'
)
st.markdown('---')

stores_dict = load_all_stores('.')
store_names = (
    sorted(list(stores_dict.keys()))
    if stores_dict
    else ['STORE1', 'STORE2', 'STORE3', 'STORE4', 'STORE5']
)

selected_store = st.sidebar.selectbox(
    'Select Store for Analysis:', store_names
)

store_data = stores_dict.get(
    selected_store, {'users': pd.DataFrame(), 'orders': pd.DataFrame(), 'books': pd.DataFrame()}
)
u_df = store_data['users']
o_df = store_data['orders']
b_df = store_data['books']

analytics = compute_store_analytics(u_df, o_df, b_df)

tab1, tab2, tab3, tab4 = st.tabs([
    f'Summary & Revenue ({selected_store})',
    f'Authors & Books ({selected_store})',
    'AI Chat Assistant',
    f'Users Data ({selected_store})',
])

with tab1:
  st.subheader(
      f'Key Metrics & Required Deliverables for **{selected_store}**'
  )

  col_m1, col_m2, col_m3 = st.columns(3)
  col_m1.metric(
      f'Unique Users (Reconciled in {selected_store})',
      f"{analytics['unique_users_count']:,}",
  )
  col_m2.metric(
      f'Unique Author Sets in {selected_store}',
      f"{analytics['unique_author_sets_count']:,}",
  )
  col_m3.metric(
      f'Most Popular Author in {selected_store}',
      f"{analytics['most_popular_author']}",
  )

  st.write(
      f'**Best Buyer in {selected_store} (with aliases array):**'
      f" `{analytics['best_buyer'].get('aliases', [])}` (Total Spending:"
      f" ${analytics['best_buyer'].get('spending', 0):,.2f})"
  )

  st.markdown('---')
  st.subheader(f'1. Top 5 Days by Revenue in {selected_store}')
  if not analytics['top_5_days'].empty:
    top_5_disp = analytics['top_5_days'].copy()
    top_5_disp.columns = ['Date (YYYY-MM-dd)', 'Total Revenue ($)']
    top_5_disp['Total Revenue ($)'] = top_5_disp['Total Revenue ($)'].map(
        '{:,.2f}'.format
    )
    st.table(top_5_disp)

    col1, col2 = st.columns(2)
    col1.metric(f'Total Orders in {selected_store}', f'{len(o_df):,}')
    col2.metric(
        f'Total Revenue in {selected_store}',
        f"${o_df['paid_price'].sum():,.2f}"
        if not o_df.empty
        else '$0.00',
    )

    st.markdown('---')
    st.subheader(
        f'Daily Revenue Trend Chart ({selected_store}) - Cleaned Spikes'
    )
    if not o_df.empty and 'date' in o_df.columns:
      daily_rev_chart = o_df.groupby('date')['paid_price'].sum().reset_index()
      st.line_chart(daily_rev_chart.set_index('date'))
  else:
    st.warning(f'No valid order data available for {selected_store}.')

with tab2:
  st.subheader(
      f'📚 Author Book Counts & Popular Authors in **{selected_store}**'
  )

  if not b_df.empty:
    auth_col = (
        'authors'
        if 'authors' in b_df.columns
        else ('author' if 'author' in b_df.columns else None)
    )
    if auth_col:
      author_counts = (
          b_df[auth_col].astype(str).value_counts().head(15).reset_index()
      )
      author_counts.columns = ['Author / Author Set', 'Book Count']
      st.markdown(
          f'**Top Authors / Author Sets by Book Count in {selected_store}:**'
      )
      st.table(author_counts)

      unique_sets_count = b_df[auth_col].astype(str).nunique()
      st.info(
          f'Number of unique author sets in {selected_store}: **'
          f'{unique_sets_count}**'
      )
    else:
      st.dataframe(b_df.head(10), width='stretch')
  else:
    st.info(f'No books.yaml data found for {selected_store}.')

with tab3:
  st.subheader('Interactive Chat Assistant (Per-Store Analysis)')
  st.markdown(
      'Ask questions specifying a store (e.g., "How many unique users are there'
      ' in the store2?", "How many books does STORE1 have?").'
  )

  if 'messages' not in st.session_state:
    st.session_state.messages = []

  for message in st.session_state.messages:
    with st.chat_message(message['role']):
      st.markdown(message['content'])

  if prompt := st.chat_input('Ask a question about the store dataset...'):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
      st.markdown(prompt)

    p = prompt.lower()
    reply = ''

    target_store = selected_store
    for s_name in store_names:
      s_num = s_name.replace('STORE', '')
      if (
          f'store {s_num}' in p
          or f'store{s_num}' in p
          or f'store {s_lower := s_num}' in p
      ):
        target_store = s_name
        break
      if f'store {s_num}' in p:
        target_store = s_name
        break

    t_data = stores_dict.get(
        target_store, {'users': pd.DataFrame(), 'orders': pd.DataFrame(), 'books': pd.DataFrame()}
    )
    t_u = t_data['users']
    t_o = t_data['orders']
    t_b = t_data['books']
    t_ana = compute_store_analytics(t_u, t_o, t_b)

    if 'unique user' in p or 'users' in p or 'customer' in p:
      reply = (
          f'In **{target_store}**, there are **'
          f"{t_ana['unique_users_count']:,}** reconciled unique users."
      )
    elif 'popular author' in p or 'most popular' in p:
      reply = (
          f'In **{target_store}**, the most popular author / author set is **'
          f"{t_ana['most_popular_author']}**."
      )
    elif 'author set' in p or 'unique sets' in p or 'sets of authors' in p:
      reply = (
          f'In **{target_store}**, there are **'
          f"{t_ana['unique_author_sets_count']:,}** unique author sets."
      )
    elif 'best buyer' in p or 'top customer' in p or 'spending' in p:
      buyer = t_ana['best_buyer']
      reply = (
          f'In **{target_store}**, the best buyer has total spending of **$'
          f"{buyer.get('spending', 0):,.2f}** with user ID aliases/variants:"
          f" `{buyer.get('aliases', [])}`."
      )
    elif 'top 5' in p or 'revenue' in p or 'sales' in p:
      top5 = t_ana['top_5_days']
      reply = f'Here are the top 5 days by revenue in **{target_store}**:\n'
      for _, row in top5.iterrows():
        reply += f"- **{row['date']}**: ${row['paid_price']:,.2f}\n"
    else:
      found_author = False
      if not t_b.empty:
        auth_col = (
            'authors'
            if 'authors' in t_b.columns
            else ('author' if 'author' in t_b.columns else None)
        )
        if auth_col:
          for auth in t_b[auth_col].astype(str).str.lower().unique():
            auth_clean = str(auth)
            keywords = [w for w in auth_clean.split() if len(w) > 3]
            if any(kw in p for kw in keywords):
              match_books = t_b[
                  t_b[auth_col].astype(str).str.lower() == auth_clean
              ]
              titles = (
                  match_books['title'].tolist()
                  if 'title' in match_books.columns
                  else []
              )
              reply += (
                  f'In **{target_store}**, author **{auth_clean.title()}** has'
                  f' written **{len(match_books)}** books:\n'
              )
              for t in titles[:10]:
                reply += f'- {t}\n'
              found_author = True
              break

      if not found_author:
        reply = (
            f'AI Assistant for **{target_store}**: analyzed query "{prompt}".'
            ' You can ask about unique users in this specific store, unique'
            ' author sets, best buyers, or author book counts!'
        )

    with st.chat_message('assistant'):
      st.markdown(reply)
    st.session_state.messages.append({'role': 'assistant', 'content': reply})

with tab4:
  st.subheader(f'Explore User Data in **{selected_store}**')
  if not u_df.empty:
    st.write(
        f'Showing records for **{selected_store}** (Total users:'
        f' {len(u_df)}):'
    )
    st.dataframe(u_df, width='stretch')
  else:
    st.info(f'No user data found for {selected_store}.')
