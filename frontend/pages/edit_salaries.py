import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# Import from parent app
from frontend.app import make_api_request, APIError, get_api_headers


def worker_management_page():
    """Worker Management Page"""
    st.markdown("## 👥 Worker Management")
    
    # Initialize session state
    if 'workers_data' not in st.session_state:
        st.session_state.workers_data = []
    if 'bank_codes' not in st.session_state:
        st.session_state.bank_codes = {}
    if 'selected_worker' not in st.session_state:
        st.session_state.selected_worker = None
    
    # Load data
    try:
        # Get workers list
        workers_response = make_api_request("/api/workers", auth_token=st.session_state.auth_token)
        st.session_state.workers_data = workers_response['workers']
        
        # Get bank codes
        bank_response = make_api_request("/api/workers/bank-codes/list", auth_token=st.session_state.auth_token)
        st.session_state.bank_codes = bank_response['bank_codes']
        
    except APIError as e:
        st.error(f"❌ Failed to load worker data: {e}")
        return
    
    # Tab navigation
    tab1, tab2, tab3 = st.tabs(["📊 View Workers", "➕ Add Worker", "✏️ Edit Worker"])
    
    with tab1:
        view_workers_tab()
    
    with tab2:
        add_worker_tab()
    
    with tab3:
        edit_worker_tab()


def view_workers_tab():
    """View and manage existing workers"""
    st.markdown("### 📊 Worker Directory")
    
    if not st.session_state.workers_data:
        st.info("📝 No workers found. Add your first worker using the 'Add Worker' tab.")
        return
    
    # Search and filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_term = st.text_input("🔍 Search Workers", placeholder="Search by name, email, or bank...")
    
    with col2:
        status_filter = st.selectbox("Status Filter", ["All", "Active", "Inactive"])
    
    with col3:
        frequency_filter = st.selectbox("Payment Frequency", ["All", "weekly", "bi-weekly", "monthly"])
    
    # Apply filters
    filtered_workers = st.session_state.workers_data.copy()
    
    if search_term:
        search_lower = search_term.lower()
        filtered_workers = [
            w for w in filtered_workers 
            if (search_lower in w['name'].lower() or 
                (w['email'] and search_lower in w['email'].lower()) or
                search_lower in w['bank_name'].lower() or
                search_lower in w['account_number'].lower())
        ]
    
    if status_filter != "All":
        is_active = status_filter == "Active"
        filtered_workers = [w for w in filtered_workers if w['is_active'] == is_active]
    
    if frequency_filter != "All":
        filtered_workers = [w for w in filtered_workers if w['payment_frequency'] == frequency_filter]
    
    # Display statistics
    total_workers = len(filtered_workers)
    active_workers = len([w for w in filtered_workers if w['is_active']])
    total_monthly_cost = sum(w['salary_amount'] for w in filtered_workers if w['is_active'])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Workers", total_workers)
    with col2:
        st.metric("Active Workers", active_workers)
    with col3:
        st.metric("Monthly Cost", f"₦{total_monthly_cost:,.2f}")
    
    # Workers table
    if filtered_workers:
        # Create DataFrame for display
        df = pd.DataFrame(filtered_workers)
        
        # Format data for display
        df_display = df.copy()
        df_display['salary_amount'] = df_display['salary_amount'].apply(lambda x: f"₦{x:,.2f}")
        df_display['status'] = df_display['is_active'].apply(lambda x: "✅ Active" if x else "❌ Inactive")
        df_display['next_payment'] = df_display['next_payment_date'].apply(
            lambda x: datetime.fromisoformat(x.replace('Z', '+00:00')).strftime('%Y-%m-%d') if x else "Not set"
        )
        
        # Select columns to display
        display_columns = ['name', 'email', 'bank_display_name', 'account_number', 'salary_amount', 
                          'payment_frequency', 'status', 'next_payment']
        column_names = ['Name', 'Email', 'Bank', 'Account', 'Salary', 'Frequency', 'Status', 'Next Payment']
        
        st.dataframe(
            df_display[display_columns].rename(columns=dict(zip(display_columns, column_names))),
            use_container_width=True,
            hide_index=True
        )
        
        # Action buttons for each worker
        st.markdown("### ⚡ Quick Actions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh Data", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📤 Export to CSV", use_container_width=True):
                csv = df_display[display_columns].to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"workers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col3:
            if st.button("💰 Process Payment for Selected", use_container_width=True):
                st.session_state.show_payment_modal = True
        
        # Individual worker actions
        st.markdown("### 👤 Worker Actions")
        for i, worker in enumerate(filtered_workers):
            with st.expander(f"👤 {worker['name']} - {worker['bank_display_name']}"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button(f"💰 Pay Now", key=f"pay_{worker['id']}", use_container_width=True):
                        process_single_payment(worker['id'], worker['name'], worker['salary_amount'])
                
                with col2:
                    if st.button(f"✏️ Edit", key=f"edit_{worker['id']}", use_container_width=True):
                        st.session_state.selected_worker = worker
                        st.rerun()
                
                with col3:
                    new_status = not worker['is_active']
                    status_text = "Activate" if new_status else "Deactivate"
                    if st.button(f"{'✅' if new_status else '❌'} {status_text}", 
                               key=f"toggle_{worker['id']}", use_container_width=True):
                        toggle_worker_status(worker['id'], new_status)
                
                with col4:
                    if st.button(f"🗑️ Delete", key=f"delete_{worker['id']}", use_container_width=True):
                        delete_worker(worker['id'], worker['name'])
    
    else:
        st.info("🔍 No workers found matching your search criteria.")


def add_worker_tab():
    """Add new worker form"""
    st.markdown("### ➕ Add New Worker")
    
    with st.form("add_worker_form"):
        # Personal Information
        st.markdown("#### 👤 Personal Information")
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name*", placeholder="Enter worker's full name")
            email = st.text_input("Email", placeholder="worker@email.com (optional)")
        
        # Bank Information
        st.markdown("#### 🏦 Bank Information")
        col1, col2 = st.columns(2)
        
        with col1:
            bank_code = st.selectbox(
                "Bank*", 
                options=list(st.session_state.bank_codes.keys()),
                format_func=lambda x: f"{x} - {st.session_state.bank_codes[x]}",
                help="Select the worker's bank"
            )
        
        with col2:
            account_number = st.text_input("Account Number*", placeholder="10-digit account number", max_chars=10)
        
        # Account verification
        if bank_code and account_number and len(account_number) == 10:
            if st.button("🔍 Verify Account", use_container_width=True):
                verify_bank_account(account_number, bank_code)
        
        # Salary Information
        st.markdown("#### 💰 Salary Information")
        col1, col2 = st.columns(2)
        
        with col1:
            salary_amount = st.number_input(
                "Monthly Salary*", 
                min_value=1000.0, 
                max_value=10000000.0,
                value=50000.0,
                step=1000.0,
                help="Monthly salary amount in Naira"
            )
        
        with col2:
            payment_frequency = st.selectbox(
                "Payment Frequency*",
                options=["monthly", "bi-weekly", "weekly"],
                format_func=lambda x: x.replace('-', ' ').title(),
                help="How often to pay this worker"
            )
        
        # Form submission
        col1, col2 = st.columns(2)
        with col1:
            submit_worker = st.form_submit_button("➕ Add Worker", use_container_width=True)
        with col2:
            clear_form = st.form_submit_button("🗑️ Clear Form", use_container_width=True)
        
        if submit_worker:
            if validate_worker_form(name, bank_code, account_number, salary_amount):
                add_worker(name, email, st.session_state.bank_codes[bank_code], 
                          account_number, bank_code, salary_amount, payment_frequency)
        
        if clear_form:
            st.rerun()


def edit_worker_tab():
    """Edit existing worker"""
    st.markdown("### ✏️ Edit Worker")
    
    if not st.session_state.workers_data:
        st.info("📝 No workers available for editing.")
        return
    
    # Select worker to edit
    worker_options = {f"{w['name']} - {w['bank_display_name']}": w for w in st.session_state.workers_data}
    selected_worker_key = st.selectbox("Select Worker to Edit", list(worker_options.keys()))
    
    if selected_worker_key:
        worker = worker_options[selected_worker_key]
        
        with st.form("edit_worker_form"):
            st.markdown(f"#### Editing: **{worker['name']}**")
            
            # Editable fields
            col1, col2 = st.columns(2)
            
            with col1:
                new_name = st.text_input("Full Name", value=worker['name'])
                new_email = st.text_input("Email", value=worker['email'] or "")
                new_salary = st.number_input(
                    "Monthly Salary", 
                    min_value=1000.0, 
                    max_value=10000000.0,
                    value=float(worker['salary_amount']),
                    step=1000.0
                )
            
            with col2:
                new_frequency = st.selectbox(
                    "Payment Frequency",
                    options=["monthly", "bi-weekly", "weekly"],
                    index=["monthly", "bi-weekly", "weekly"].index(worker['payment_frequency']),
                    format_func=lambda x: x.replace('-', ' ').title()
                )
                
                new_bank_code = st.selectbox(
                    "Bank Code",
                    options=list(st.session_state.bank_codes.keys()),
                    index=list(st.session_state.bank_codes.keys()).index(worker['bank_code']),
                    format_func=lambda x: f"{x} - {st.session_state.bank_codes[x]}"
                )
                
                new_account_number = st.text_input(
                    "Account Number", 
                    value=worker['account_number'],
                    max_chars=10
                )
                
                is_active = st.checkbox("Active", value=worker['is_active'])
            
            # Form submission
            col1, col2 = st.columns(2)
            with col1:
                update_worker_btn = st.form_submit_button("✏️ Update Worker", use_container_width=True)
            with col2:
                cancel_edit = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if update_worker_btn:
                update_worker(
                    worker['id'], new_name, new_email, 
                    st.session_state.bank_codes[new_bank_code], new_account_number,
                    new_bank_code, new_salary, new_frequency, is_active
                )
            
            if cancel_edit:
                st.session_state.selected_worker = None
                st.rerun()


def process_single_payment(worker_id: int, worker_name: str, amount: float):
    """Process payment for a single worker"""
    try:
        payment_data = {"worker_id": worker_id}
        response = make_api_request(
            "/api/payments/process", 
            "POST", 
            payment_data, 
            st.session_state.auth_token
        )
        
        st.success(f"✅ Payment processed for {worker_name}! Reference: {response['transaction_reference']}")
        st.rerun()
        
    except APIError as e:
        st.error(f"❌ Payment failed for {worker_name}: {e}")


def toggle_worker_status(worker_id: int, new_status: bool):
    """Toggle worker active status"""
    try:
        worker_data = {"is_active": new_status}
        make_api_request(
            f"/api/workers/{worker_id}", 
            "PUT", 
            worker_data, 
            st.session_state.auth_token
        )
        
        status_text = "activated" if new_status else "deactivated"
        st.success(f"✅ Worker {status_text} successfully!")
        st.rerun()
        
    except APIError as e:
        st.error(f"❌ Failed to update worker status: {e}")


def delete_worker(worker_id: int, worker_name: str):
    """Delete/deactivate worker"""
    try:
        make_api_request(
            f"/api/workers/{worker_id}", 
            "DELETE", 
            auth_token=st.session_state.auth_token
        )
        
        st.success(f"✅ Worker {worker_name} has been deactivated!")
        st.rerun()
        
    except APIError as e:
        st.error(f"❌ Failed to deactivate worker: {e}")


def verify_bank_account(account_number: str, bank_code: str):
    """Verify bank account details"""
    try:
        # This would call an account verification endpoint
        # For now, just show a placeholder message
        st.info("🔍 Account verification feature will be available with Paystack account validation API")
        
    except Exception as e:
        st.error(f"❌ Account verification failed: {e}")


def validate_worker_form(name: str, bank_code: str, account_number: str, salary_amount: float) -> bool:
    """Validate worker form data"""
    if not name.strip():
        st.error("❌ Full name is required")
        return False
    
    if not bank_code:
        st.error("❌ Bank selection is required")
        return False
    
    if not account_number or len(account_number) != 10:
        st.error("❌ Valid 10-digit account number is required")
        return False
    
    if not account_number.isdigit():
        st.error("❌ Account number must contain only digits")
        return False
    
    if salary_amount <= 0:
        st.error("❌ Salary amount must be positive")
        return False
    
    return True


def add_worker(name: str, email: str, bank_name: str, account_number: str, 
               bank_code: str, salary_amount: float, payment_frequency: str):
    """Add new worker"""
    try:
        worker_data = {
            "name": name.strip(),
            "email": email.strip() if email.strip() else None,
            "bank_name": bank_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "salary_amount": salary_amount,
            "payment_frequency": payment_frequency
        }
        
        response = make_api_request(
            "/api/workers", 
            "POST", 
            worker_data, 
            st.session_state.auth_token
        )
        
        st.success(f"✅ Worker '{name}' added successfully!")
        st.rerun()
        
    except APIError as e:
        st.error(f"❌ Failed to add worker: {e}")


def update_worker(worker_id: int, name: str, email: str, bank_name: str, 
                 account_number: str, bank_code: str, salary_amount: float, 
                 payment_frequency: str, is_active: bool):
    """Update existing worker"""
    try:
        worker_data = {
            "name": name.strip(),
            "email": email.strip() if email.strip() else None,
            "bank_name": bank_name,
            "account_number": account_number,
            "bank_code": bank_code,
            "salary_amount": salary_amount,
            "payment_frequency": payment_frequency,
            "is_active": is_active
        }
        
        response = make_api_request(
            f"/api/workers/{worker_id}", 
            "PUT", 
            worker_data, 
            st.session_state.auth_token
        )
        
        st.success(f"✅ Worker '{name}' updated successfully!")
        st.session_state.selected_worker = None
        st.rerun()
        
    except APIError as e:
        st.error(f"❌ Failed to update worker: {e}")
