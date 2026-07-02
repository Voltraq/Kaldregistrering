import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Call Reasons", page_icon="📞")

# --- 2. PERSONLIGT LOGIN SYSTEM ---
def login_flow():
    """Håndterer personligt login og gemmer operatørens navn i sessionen."""
    # Hvis brugeren allerede er logget ind, send dem videre
    if "operator" in st.session_state:
        return True
    
    st.title("📞 Kundecenter Log ind")
    st.write("Indtast dine initialer og din personlige adgangskode for at starte.")
    
    with st.form("login_form"):
        # Gør automatisk brugernavnet til store bogstaver, så det altid matcher (f.eks. kaf -> KAF)
        username = st.text_input("Brugernavn (Initialer)").upper().strip()
        password = st.text_input("Adgangskode", type="password")
        submit_login = st.form_submit_button("Log ind", type="primary")
        
        if submit_login:
            # Tjek om brugeren findes i vores secrets, og om koden passer
            if username in st.secrets["users"] and password == st.secrets["users"][username]:
                st.session_state["operator"] = username
                st.rerun()  # Genindlæs siden så hovedappen vises
            else:
                st.error("⚠️ Forkert brugernavn eller adgangskode. Prøv igen.")
    return False

# --- 3. HOVEDAPP ---
if login_flow():
    
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

    # Vis hvem der er logget ind i toppen, samt en Log ud-knap
    col_header, col_logout = st.columns([3, 1])
    with col_header:
        st.title("📞 Call Reasons")
        st.caption(f"Logget ind som: **{st.session_state['operator']}**")
    with col_logout:
        if st.button("Log ud"):
            del st.session_state["operator"]
            st.rerun()

    # --- INPUT FORM ---
    with st.form("call_form", clear_on_submit=True):
        
        # Vi har nu kun brug for én kolonne, da operatøren er kendt
        call_reason = st.selectbox("Reason for Call", 
            ["Spørgsmål til slutopgørelse", "Fejl med regning", "Tekniske spørgsmål", "Spørgsmål til kontrakt", 
             "Klage", "Generelt spørgsmål", "Rykker", "Opsigelse", "Restgæld", "Indfrielse", "Kontrakt ændringer"],
            index=None,
            placeholder="Vælg årsag..."
        )
                
        notes = st.text_area("Additional Notes")
        submitted = st.form_submit_button("Register Call", type="primary")

        if submitted:
            if not call_reason:
                st.warning("Vælg venligst en årsag til opkaldet.")
            else:
                today_str = datetime.now().strftime("%Y-%m-%d")
                time_str = datetime.now().strftime("%H:%M:%S")
                
                # Byg datapakken. Den trækker automatisk "operator" fra hukommelsen
                new_data = {
                    "date": today_str,
                    "time": time_str,
                    "operator": st.session_state["operator"],
                    "reason": call_reason,
                    "notes": notes
                }
                
                # Indsæt i Supabase databasen
                try:
                    supabase.table("call_logs").insert(new_data).execute()
                    st.success(f"✅ Kald registreret af {st.session_state['operator']}!")
                except Exception as e:
                    st.error(f"Fejl ved gem: {e}")

    # --- VIS LOG FOR I DAG ---
    st.divider()
    if st.checkbox("Show Today's Log"):
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = supabase.table("call_logs").select("time, operator, reason, notes").eq("date", today_str).order("id", desc=True).execute()
            data = response.data
            
            if data:
                df_today = pd.DataFrame(data)
                df_today.columns = [col.capitalize() for col in df_today.columns]
                st.dataframe(df_today, use_container_width=True, hide_index=True)
            else:
                st.info("Ingen opkald registreret endnu i dag.")
        except Exception as e:
            st.error(f"Kunne ikke hente loggen: {e}")
