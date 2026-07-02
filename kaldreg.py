import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Call Reasons", page_icon="📞")

# --- 2. ADGANGSKODE SIKRING ---
def check_password():
    """Returnerer True hvis brugeren har indtastet den rette kode."""
    if st.session_state.get("password_correct", False):
        return True
    
    st.title("📞 Opkaldsregistrering — Log ind")
    st.write("Dette system er lukket for offentligheden. Venligst log ind nedenfor.")
    
    try:
        correct_password = st.secrets["general"]["app_password"]
    except KeyError:
        st.error("Fejl: 'app_password' er ikke opsat i Streamlit Secrets endnu.")
        return False

    password = st.text_input("Indtast adgangskode:", type="password")
    if st.button("Log ind", type="primary"):
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("⚠️ Forkert adgangskode. Prøv igen.")
    return False

# --- 3. HOVEDAPP ---
if check_password():
    
    # Etabler forbindelse til Supabase (Gemmes i cache for at gøre appen hurtigere)
    @st.cache_resource
    def init_connection():
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)

    try:
        supabase = init_connection()
    except Exception as e:
        st.error("Kunne ikke forbinde til databasen. Tjek dine secrets.")
        st.stop()

    st.title("📞 Call Reasons")
    st.caption("Data gemmes sikkert i skyen via Supabase")

    # --- INPUT FORM ---
    with st.form("call_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            operator_name = st.selectbox("Operator Name", 
                ["KAF", "LUJ", "KLN", "DIB", "SBN", "NHA", "IEK", "GIJ", "KSL"])
                
        with col2:
            call_reason = st.selectbox("Reason for Call", 
                ["Spørgsmål til slutopgørelse", "Fejl med regning", "Tekniske spørgsmål", "Spørgsmål til kontrakt", 
                 "Klage", "Generelt spørgsmål", "Rykker", "Opsigelse", "Restgæld", "Indfrielse", "Kontrakt ændringer"])
                
        notes = st.text_area("Additional Notes")
        submitted = st.form_submit_button("Register Call", type="primary")

        if submitted:
            if not operator_name:
                st.warning("Please select an operator name.")
            else:
                today_str = datetime.now().strftime("%Y-%m-%d")
                time_str = datetime.now().strftime("%H:%M:%S")
                
                # Byg datapakken
                new_data = {
                    "date": today_str,
                    "time": time_str,
                    "operator": operator_name,
                    "reason": call_reason,
                    "notes": notes
                }
                
                # Indsæt i Supabase databasen
                try:
                    supabase.table("call_logs").insert(new_data).execute()
                    st.success("✅ Call registered successfully!")
                except Exception as e:
                    st.error(f"Fejl ved gem: {e}")

    # --- VIS LOG FOR I DAG ---
    st.divider()
    if st.checkbox("Show Today's Log"):
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Hent kun dagens data fra databasen
        try:
            response = supabase.table("call_logs").select("time, operator, reason, notes").eq("date", today_str).order("id", desc=True).execute()
            data = response.data
            
            if data:
                # Lav det om til en pæn Pandas DataFrame og vis det
                df_today = pd.DataFrame(data)
                
                # Omdøb kolonnerne så de ser pæne ud med stort begyndelsesbogstav
                df_today.columns = [col.capitalize() for col in df_today.columns]
                
                st.dataframe(df_today, use_container_width=True, hide_index=True)
            else:
                st.info("No calls registered yet today.")
        except Exception as e:
            st.error(f"Kunne ikke hente loggen: {e}")