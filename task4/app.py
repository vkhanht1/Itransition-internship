import pandas as pd
import streamlit as st
from process_data import compute_analytics, load_and_process_all_stores

st.set_page_config(page_title='Task 4 - BI Dashboard', layout='wide')

st.title('Business Intelligence Dashboard - Task 4 Analysis')
st.markdown('---')

orders_df, users_df, books_df = load_and_process_all_stores('.')
analytics = compute_analytics(orders_df, users_df, books_df)

tab1, tab2, tab3, tab4 = st.tabs([
    'Revenue & Summary',
    'Authors & Books Analysis',
    'AI Chat Assistant',
    'Stores & Users Data',
])

with tab1:
  st.subheader('Key Metrics & Required Deliverables')

  col_m1, col_m2, col_m3 = st.columns(3)
  col_m1.metric(
      'Number of Unique Users (Reconciled)',
      f"{analytics['unique_users_count']:,}",
  )
  col_m2.metric(
      'Unique Author Sets', f"{analytics['unique_author_sets_count']:,}"
  )
  col_m3.metric('Most Popular Author / Set', f"{analytics['most_popular_author']}")

  st.write(
      '**Best Buyer (with aliases array):**'
      f" `{analytics['best_buyer'].get('aliases', [])}` (Total Spending:"
      f" ${analytics['best_buyer'].get('spending', 0):,.2f})"
  )

  st.markdown('---')
  st.subheader('1. Top 5 Days by Revenue (YYYY-MM-dd)')
  if not analytics['top_5_days'].empty:
    top_5_disp = analytics['top_5_days'].copy()
    top_5_disp.columns = ['Date (YYYY-MM-dd)', 'Total Revenue ($)']
    top_5_disp['Total Revenue ($)'] = top_5_disp['Total Revenue ($)'].map(
        '{:,.2f}'.format
    )
    st.table(top_5_disp)

    col1, col2 = st.columns(2)
    col1.metric('Total Orders Processed', f'{len(orders_df):,}')
    total_rev = analytics['top_5_days']['paid_price'].sum()  # or total rev
    col2.metric(
        'Total System Revenue', f"${orders_df['paid_price'].sum():,.2f}"
    )

    st.markdown('---')
    st.subheader('Daily Revenue Trend Chart')
    if 'date' in orders_df.columns:
      daily_rev_chart = (
          orders_df.groupby('date')['paid_price'].sum().reset_index()
      )
      st.line_chart(daily_rev_chart.set_index('date'))
  else:
    st.warning('No valid order data available.')

with tab2:
  st.subheader(
      'Author Sets & Most Popular Author Analysis (Parts 2 & 3)'
  )

  if not books_df.empty and 'store' in books_df.columns:
    store_list_books = sorted(books_df['store'].unique())
    selected_book_store = st.selectbox(
        'Select store location for books analysis:',
        store_list_books,
        key='book_store_select',
    )

    filtered_books = books_df[books_df['store'] == selected_book_store]
    st.write(
        f'Total book records in **{selected_book_store}**: **'
        f'{len(filtered_books)}** items.'
    )

    if 'authors' in filtered_books.columns:
      author_counts = (
          filtered_books['authors']
          .astype(str)
          .value_counts()
          .head(10)
          .reset_index()
      )
      author_counts.columns = ['Author / Author Set', 'Book Count']
      st.markdown(
          f'**Top Popular Authors / Author Sets in {selected_book_store}:**'
      )
      st.table(author_counts)

      unique_sets_count = filtered_books['authors'].astype(str).nunique()
      st.info(
          f'Number of unique author sets in {selected_book_store}: **'
          f'{unique_sets_count}**'
      )
    else:
      st.dataframe(filtered_books.head(10), width='stretch')
  else:
    st.info('No books.yaml data found.')

with tab3:
  st.subheader('Interactive Chat Assistant (Parts 2 & 3 Analysis)')
  st.markdown(
      'Ask questions about unique users, author sets, best buyers, or specific'
      ' authors (e.g., "How many different books are written by Amb. September'
      ' Walter?").'
  )

  if 'messages' not in st.session_state:
    st.session_state.messages = []

  for message in st.session_state.messages:
    with st.chat_message(message['role']):
      st.markdown(message['content'])

  if prompt := st.chat_input('Ask a question about the dataset or authors...'):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
      st.markdown(prompt)

    p = prompt.lower()
    if 'unique user' in p or 'users' in p:
      reply = (
          'There are **'
          f"{analytics['unique_users_count']:,}** real unique users in the"
          ' system after data reconciliation (matching records where at most 1'
          ' field changed).'
      )
    elif 'author set' in p or 'unique sets' in p:
      reply = (
          'There are **'
          f"{analytics['unique_author_sets_count']:,}** unique author sets"
          ' identified across all stores.'
      )
    elif 'popular author' in p or 'most popular' in p:
      reply = (
          'The most popular author / author set is **'
          f"{analytics['most_popular_author']}**."
      )
    elif 'best buyer' in p or 'top customer' in p or 'spending' in p:
      buyer = analytics['best_buyer']
      reply = (
          'The best buyer has total spending of **$'
          f"{buyer.get('spending', 0)::,.2f}** with user ID aliases/variants:"
          f" `{buyer.get('aliases', [])}`."
      )
    elif 'top 5' in p or 'revenue' in p:
      top5 = analytics['top_5_days']
      reply = 'Here are the top 5 days by revenue:\n'
      for _, row in top5.iterrows():
        reply += f"- **{row['date']}**: ${row['paid_price']:,.2f}\n"
    else:
      found_author = False
      reply = ''
      if not books_df.empty:
        for auth in books_df['authors'].astype(str.lower()).unique():
          auth_clean = str(auth)
          if any(
              w in p
              for w in auth_clean.split()
              if len(w) > 3 and w not in ['written', 'books', 'how', 'many']
          ):
            match_books = books_df[
                books_df['authors'].astype(str).str.lower() == auth_clean
            ]
            titles = (
                match_books['title'].tolist()
                if 'title' in match_books.columns
                else []
            )
            reply += (
                f'Author **{auth_clean.title()}** has written **'
                f'{len(match_books)}** different books:\n'
            )
            for t in titles[:10]:
              reply += f'- {t}\n'
            found_author = True
            break

      if not found_author:
        reply = (
            f'AI Assistant analyzed your query: "{prompt}". Total stores:'
            f' 5 | Total orders: {len(orders_df):,} | Total books:'
            f' {len(books_df):,}. You can ask about unique users, unique author'
            ' sets, best buyer IDs, or specific author book counts!'
        )

    with st.chat_message('assistant'):
      st.markdown(reply)
    st.session_state.messages.append({'role': 'assistant', 'content': reply})

with tab4:
  st.subheader('Explore User Data by Store')

  if not users_df.empty and 'store' in users_df.columns:
    store_list = sorted(users_df['store'].unique())
    selected_store = st.selectbox(
        'Select store location to inspect:', store_list, key='user_store_select'
    )

    filtered_users = users_df[users_df['store'] == selected_store]
    len_users = len(filtered_users)

    st.write(
        f'Showing records for **{selected_store}** (Total users in this store:'
        f' {len_users}):'
    )
    st.dataframe(filtered_users, width='stretch')
  else:
    st.info('No user data found.')
