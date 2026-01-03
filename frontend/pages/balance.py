import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# Import from parent app
from frontend.app import make_api_request, APIError, get_api_headers


def balance_page():
    """Balance Dashboard Page"""
    st.markdown("## 💰 Balance Dashboard")
    
    # Initialize session state for refresh
    if 'balance_data' not in st.session_state:
        st.session_state.balance_data = None
    if 'payment_history' not in st.session_state:
        st.session_state.payment_history = []
    if 'stats_data' not in st.session_state:
        st.session_state.stats_data = None
    
    # Load data
    try:
        # Get balance
        balance_response = make_api_request("/api/payments/balance", auth_token=st.session_state.auth_token)
        st.session_state.balance_data = balance_response
        
        # Get payment statistics
        stats_response = make_api_request("/api/payments/stats", auth_token=st.session_state.auth_token)
        st.session_state.stats_data = stats_response
        
        # Get recent payment history (last 20 payments)
        payment_history = make_api_request(
            "/api/payments/history?limit=20", 
            auth_token=st.session_state.auth_token
        )
        st.session_state.payment_history = payment_history
        
    except APIError as e:
        st.error(f"❌ Failed to load dashboard data: {e}")
        return
    
    # Dashboard Metrics
    if st.session_state.balance_data and st.session_state.stats_data:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            balance = st.session_state.balance_data['balance']
            st.metric(
                "Current Balance",
                f"₦{balance:,.2f}",
                help="Current Paystack account balance"
            )
        
        with col2:
            active_workers = st.session_state.stats_data['active_workers']
            st.metric(
                "Active Workers",
                active_workers,
                help="Number of active workers"
            )
        
        with col3:
            monthly_cost = st.session_state.stats_data['monthly_cost']
            st.metric(
                "Monthly Cost",
                f"₦{monthly_cost:,.2f}",
                help="Total monthly payroll cost"
            )
        
        with col4:
            pending = st.session_state.stats_data['pending_payments']
            st.metric(
                "Pending Payments",
                pending,
                help="Number of pending payments"
            )
        
        # Balance Health Check
        if st.session_state.balance_data['balance'] < st.session_state.stats_data['monthly_cost']:
            st.warning("⚠️ **Low Balance Warning**: Current balance is below monthly payroll cost!")
        elif st.session_state.balance_data['balance'] < st.session_state.stats_data['monthly_cost'] * 0.5:
            st.info("ℹ️ **Balance Notice**: Consider adding funds to ensure smooth operations.")
        else:
            st.success("✅ **Balance Healthy**: Sufficient funds for payroll operations.")
    
    # Quick Actions Section
    st.markdown("---")
    st.markdown("### ⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Balance", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("📊 View Payment History", use_container_width=True):
            st.session_state.show_payment_history = True
    
    with col3:
        if st.button("💰 Process Manual Payment", use_container_width=True):
            st.session_state.show_payment_form = True
    
    # Payment Form Modal
    if st.session_state.get('show_payment_form', False):
        st.markdown("---")
        st.markdown("### 💳 Process Manual Payment")
        
        with st.form("manual_payment_form"):
            try:
                # Get workers list
                workers_response = make_api_request("/api/workers?active_only=true", auth_token=st.session_state.auth_token)
                workers = workers_response['workers']
                
                worker_options = {f"{w['name']} (₦{w['salary_amount']:,.2f})": w['id'] for w in workers}
                
                selected_worker = st.selectbox("Select Worker", list(worker_options.keys()))
                custom_amount = st.number_input(
                    "Custom Amount (leave empty to use salary)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="Leave as 0 to use the worker's regular salary amount"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_payment = st.form_submit_button("💰 Process Payment", use_container_width=True)
                with col2:
                    cancel_payment = st.form_submit_button("❌ Cancel", use_container_width=True)
                
                if submit_payment:
                    if selected_worker:
                        try:
                            worker_id = worker_options[selected_worker]
                            amount = custom_amount if custom_amount > 0 else None
                            
                            payment_data = {
                                "worker_id": worker_id,
                                "amount": amount
                            }
                            
                            response = make_api_request(
                                "/api/payments/process", 
                                "POST", 
                                payment_data, 
                                st.session_state.auth_token
                            )
                            
                            st.success(f"✅ Payment processed successfully! Reference: {response['transaction_reference']}")
                            st.session_state.show_payment_form = False
                            st.rerun()
                            
                        except APIError as e:
                            st.error(f"❌ Payment failed: {e}")
                    else:
                        st.error("Please select a worker")
                
                if cancel_payment:
                    st.session_state.show_payment_form = False
                    st.rerun()
                    
            except APIError as e:
                st.error(f"❌ Failed to load workers: {e}")
    
    # Payment History Section
    if st.session_state.get('show_payment_history', False):
        st.markdown("---")
        st.markdown("### 📊 Payment History")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("Status Filter", ["All", "success", "pending", "failed"])
        with col2:
            days_filter = st.selectbox("Time Period", ["All", "Last 7 days", "Last 30 days", "Last 90 days"])
        with col3:
            if st.button("🔄 Refresh History", use_container_width=True):
                st.rerun()
        
        # Apply filters
        filtered_payments = st.session_state.payment_history.copy()
        
        if status_filter != "All":
            filtered_payments = [p for p in filtered_payments if p['status'] == status_filter]
        
        if days_filter != "All":
            days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
            days_back = days_map.get(days_filter, 0)
            cutoff_date = datetime.now() - timedelta(days=days_back)
            filtered_payments = [
                p for p in filtered_payments 
                if datetime.fromisoformat(p['created_at'].replace('Z', '+00:00')) >= cutoff_date
            ]
        
        # Display payment history table
        if filtered_payments:
            # Create DataFrame
            df = pd.DataFrame(filtered_payments)
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['paid_at'] = pd.to_datetime(df['paid_at'], errors='coerce')
            
            # Format columns
            df['amount'] = df['amount'].apply(lambda x: f"₦{x:,.2f}")
            df['status'] = df['status'].apply(lambda x: f"✅ {x}" if x == "success" else f"⏳ {x}" if x == "pending" else f"❌ {x}")
            
            # Select and rename columns for display
            display_df = df[['worker_name', 'amount', 'status', 'created_at', 'paid_at', 'transaction_reference']].copy()
            display_df.columns = ['Worker', 'Amount', 'Status', 'Created', 'Paid At', 'Reference']
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                total_payments = len(filtered_payments)
                st.metric("Total Payments", total_payments)
            
            with col2:
                successful_payments = len([p for p in filtered_payments if p['status'] == 'success'])
                st.metric("Successful", successful_payments)
            
            with col3:
                total_amount = sum(p['amount'] for p in filtered_payments)
                st.metric("Total Amount", f"₦{total_amount:,.2f}")
            
        else:
            st.info("📝 No payment history found with the selected filters.")
        
        # Close button
        if st.button("❌ Close History"):
            st.session_state.show_payment_history = False
            st.rerun()
    
    # Charts Section (if data available)
    if st.session_state.payment_history:
        st.markdown("---")
        st.markdown("### 📈 Payment Analytics")
        
        # Create charts from payment history
        df = pd.DataFrame(st.session_state.payment_history)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['month'] = df['created_at'].dt.to_period('M')
        
        # Payment status distribution
        status_counts = df['status'].value_counts()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for status distribution
            fig_pie = px.pie(
                values=status_counts.values,
                names=status_counts.index,
                title="Payment Status Distribution"
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            # Bar chart for monthly payments
            monthly_stats = df.groupby(['month', 'status']).size().unstack(fill_value=0)
            monthly_stats.index = monthly_stats.index.astype(str)
            
            fig_bar = px.bar(
                monthly_stats,
                title="Monthly Payment Trends",
                labels={'value': 'Number of Payments', 'index': 'Month'}
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Last updated info
    if st.session_state.balance_data:
        last_updated = st.session_state.balance_data.get('last_updated', 'Unknown')
        st.markdown(f"*Last updated: {last_updated}*")


def get_balance_data():
    """Get current balance data"""
    return make_api_request("/api/payments/balance", auth_token=st.session_state.auth_token)


def get_payment_stats():
    """Get payment statistics"""
    return make_api_request("/api/payments/stats", auth_token=st.session_state.auth_token)


def get_payment_history(limit=50):
    """Get payment history"""
    return make_api_request(f"/api/payments/history?limit={limit}", auth_token=st.session_state.auth_token)


def process_payment(worker_id, amount=None):
    """Process a payment"""
    payment_data = {"worker_id": worker_id}
    if amount:
        payment_data["amount"] = amount
    
    return make_api_request(
        "/api/payments/process", 
        "POST", 
        payment_data, 
        st.session_state.auth_token
    )
