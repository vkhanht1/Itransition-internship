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

  st.subheader(f"Daily Revenue Trend Chart ({selected_store}) - Cleaned")
  if not orders_df.empty and "date" in orders_df.columns:
    daily_chart_data = (
        orders_df.groupby("date")["paid_price"].sum().reset_index()
    )
    st.line_chart(daily_chart_data.set_index("date"), width="stretch")
  else:
    st.warning("No chart data available.")

  st.markdown("---")
  st.subheader(f"Assistant Query Interface ({selected_store})")
  st.caption(
      "Ask analytical questions about this specific store dataset. Answers"
      " are computed dynamically from the underlying data."
  )

  st.markdown(
      "**Suggested questions you can try:**\n"
      "- *'How many unique users are there?'*\n"
      "- *'Who is the most popular author?'*\n"
      "- *'What are the top revenue days?'*"
  )

  user_query = st.text_input(
      "Ask a question about the dataset (e.g., unique users, popular author,"
      " revenue):"
  )

  if user_query:
    query_lower = user_query.lower()

    if "user" in query_lower:
      st.success(
          f"In **{selected_store}**, after data reconciliation, there are"
          f" **{analytics['unique_users_count']:,}** unique users."
      )
    elif "author" in query_lower or "book" in query_lower:
      st.success(
          f"In **{selected_store}**, the most popular author is"
          f" **{analytics['most_popular_author']}** with unique author sets"
          f" count of {analytics['unique_author_sets_count']}."
      )
    elif "revenue" in query_lower or "day" in query_lower:
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
    else:
      st.info(
          f"Analyzing **{selected_store}** dataset: Total orders ="
          f" {len(orders_df):,}, Total revenue ="
          f" ${orders_df['paid_price'].sum():,.2f}."
      )