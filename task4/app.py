import os
import pandas as pd
import streamlit as st
from process_data import compute_store_analytics, load_all_stores

st.set_page_config(
    page_title="Task 4 - BI Dashboard (Per-Store)", layout="wide"
)

st.title("Task 4 - BI Dashboard & Per-Store Analytics")

stores_dict = load_all_stores()

if not stores_dict:
  st.error(
      "No STORE folders found! Please ensure STORE1 to STORE5 folders are in the"
      " directory."
  )
else:
  selected_store = st.sidebar.selectbox(
      "Select Store for Analysis:", list(stores_dict.keys())
  )

  store_data = stores_dict[selected_store]
  users_df = store_data["users"]
  orders_df = store_data["orders"]
  books_df = store_data["books"]

  analytics = compute_store_analytics(users_df, orders_df, books_df)

  col1, col2 = st.columns(2)
  col1.metric(
      f"Total Orders in {selected_store}",
      f"{len(orders_df):,}" if not orders_df.empty else "0",
  )
  total_rev = (
      orders_df["paid_price"].sum()
      if not orders_df.empty and "paid_price" in orders_df.columns
      else 0.0
  )
  col2.metric(f"Total Revenue in {selected_store}", f"${total_rev:,.2f}")

  st.subheader(f"Top Revenue Days in {selected_store}")
  if not analytics["top_5_days"].empty:
    st.dataframe(analytics["top_5_days"], width="stretch")
  else:
    st.info("No order data available for this store.")

  st.subheader(f"Daily Revenue Trend Chart ({selected_store})")
  if not orders_df.empty and "date" in orders_df.columns:
    daily_chart_data = (
        orders_df.groupby("date")["paid_price"].sum().reset_index()
    )
    st.line_chart(daily_chart_data.set_index("date"), width="stretch")
  else:
    st.warning("No chart data available.")

  st.markdown("---")
  with st.expander(
      f"View Users & Reconciliation Inspector for {selected_store}"
  ):
    st.caption(
        f"Inspect raw user records loaded from `{selected_store}/users.csv` to"
        " verify data reconciliation (e.g., duplicate detection)."
    )
    if not users_df.empty:
      search_user = st.text_input(
          f"Search user in {selected_store} (Name, Email, Phone...):",
          key=f"search_u_{selected_store}",
      )
      df_u_show = users_df
      if search_user:
        mask = (
            df_u_show.astype(str)
            .apply(lambda x: x.str.contains(search_user, case=False))
            .any(axis=1)
        )
        df_u_show = df_u_show[mask]

      st.dataframe(df_u_show, width="stretch")
      st.info(
          f"Total raw user records in {selected_store}: **{len(users_df):,}** |"
          f" Unique users after reconciliation:"
          f" **{analytics['unique_users_count']:,}**"
      )
    else:
      st.warning(f"No user data available for {selected_store}.")

  st.markdown("---")
  st.subheader(f"Assistant Query Interface ({selected_store})")
  st.caption(
      "Ask analytical questions about this specific store dataset. The"
      " assistant performs dynamic entity extraction and dataset querying."
  )

  st.markdown(
      "**Suggested questions you can try:**\n"
      "- *'How many unique users are there?'*\n"
      "- *'Who is the most popular author?'*\n"
      "- *'How many books were written by [Author Name]?'*\n"
      "- *'What are the top revenue days?'*"
  )

  user_query = st.text_input(
      "Ask a question about the dataset (e.g., unique users, specific author,"
      " revenue):"
  )

  if user_query:
    query_lower = user_query.lower()
    handled = False

    if "user" in query_lower:
      st.success(
          f"In **{selected_store}**, after data reconciliation, there are"
          f" **{analytics['unique_users_count']:,}** unique users."
      )
      handled = True

    elif not books_df.empty and "authors" in books_df.columns:
      all_authors = set()
      for authors_val in books_df["authors"].dropna():
        for a in str(authors_val).split(","):
          if a.strip():
            all_authors.add(a.strip())

      matched_author = None
      for auth in all_authors:
        if auth.lower() in query_lower:
          matched_author = auth
          break

      if matched_author:
        author_books = books_df[
            books_df["authors"]
            .str.lower()
            .str.contains(matched_author.lower(), na=False)
        ]
        st.success(
            f"In **{selected_store}**, the author **{matched_author}** has"
            f" **{len(author_books)}** books listed in the catalog."
        )
        handled = True
      elif "author" in query_lower or "book" in query_lower:
        st.success(
            f"In **{selected_store}**, the most popular author is"
            f" **{analytics['most_popular_author']}** with unique author sets"
            f" count of {analytics['unique_author_sets_count']}."
        )
        handled = True

    if not handled and ("revenue" in query_lower or "day" in query_lower):
      top_day = (
          analytics["top_5_days"].iloc[0]["date"]
          if not analytics["top_5_days"].empty
          else "N/A"
      )
      top_rev = (
          analytics["top_5_days"].iloc[0]["paid_price"]
          if not analytics["top_5_days"].empty
          else 0
      )
      st.success(
          f"In **{selected_store}**, the top revenue date is **{top_day}**"
          f" with **${top_rev:,.2f}**."
      )
      handled = True

    if not handled:
      st.info(
          f"Analyzing **{selected_store}** dataset: Total orders ="
          f" {len(orders_df):,}, Total revenue ="
          f" ${orders_df['paid_price'].sum():,.2f}, Unique users ="
          f" {analytics['unique_users_count']:,}."
      )
