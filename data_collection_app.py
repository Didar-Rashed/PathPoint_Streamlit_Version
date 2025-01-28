import streamlit as st
import os
import certifi
from datetime import datetime
import gspread
import uuid
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import date
import re
import pandas as pd

# Set environment variable for SSL
os.environ['SSL_CERT_FILE'] = certifi.where()
st.set_page_config(page_title="AOPL PathPoint", layout="centered", initial_sidebar_state="collapsed")

# Constant for time format
TIME_FORMAT = "%I:%M %p"  # 12-hour format with AM/PM

# Google Sheets connection
def connect_to_gsheet(sheet_name="PathPoint_Streemlit_Version"):
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            r'C:\Users\didar1004064\Documents\Streamlit_Data_Collection_App\elemental-leaf-447704-i9-3d3fed72129b.json', scope
        )
        client = gspread.authorize(credentials)
        return client.open(sheet_name)
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {e}")
        return None

# Google Drive image upload
def upload_to_google_drive(image):
    if not image:
        return None
    try:
        credentials = Credentials.from_service_account_file(
            r'C:\Users\didar1004064\Documents\Streamlit_Data_Collection_App\elemental-leaf-447704-i9-3d3fed72129b.json',
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        image_bytes = io.BytesIO(image.getvalue())
        media = MediaIoBaseUpload(image_bytes, mimetype='image/jpeg')
        file_metadata = {'name': 'uploaded_image.jpg'}
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return f"https://drive.google.com/uc?export=view&id={file.get('id')}"
    except Exception as e:
        st.error(f"Failed to upload image to Google Drive: {e}")
        return None

# Function to format time as 12-hour format
def format_time(hour, minute, am_pm):
    try:
        time_str = f"{hour}:{minute} {am_pm}"
        time_obj = datetime.strptime(time_str, TIME_FORMAT)
        return time_obj.strftime(TIME_FORMAT)
    except ValueError:
        return None
    


# Registration Page


def registration_page():
    st.title("Register for AOPL PathPoint")
    
    # Connect to Google Sheets
    sheet = connect_to_gsheet("PathPoint_Streemlit_Version")
    users_sheet = sheet.worksheet("Users") if sheet else None

    if not users_sheet:
        st.error("Failed to connect to the Users database.")
        return

    # Registration form
    st.subheader("Please fill in your details:")
    name = st.text_input("👤 Full Name", placeholder="Enter your full name")
    phone = st.text_input("📱 Phone Number", placeholder="Enter your phone number")
    email = st.text_input("✉️ Email", placeholder="Enter your email address")
    staff_id = st.text_input("🆔 Staff ID", placeholder="Enter your staff ID")

    if st.button("Register Me!"):
        if not name or not phone or not email or not staff_id:
            st.error("All fields are required.")
        else:
            # Check if user already exists
            records = users_sheet.get_all_records()
            if any(record["Email"] == email for record in records):
                st.error("This email is already registered! Please log in.")
                st.session_state["registered_email"] = email
                st.rerun()
            else:
                # Register user
                unique_id = str(uuid.uuid4())
                users_sheet.append_row([unique_id, name, phone, email, staff_id])
                st.success("🎉 Registration successful!")
                st.session_state["user_email"] = email
                st.session_state["user_name"] = name
                st.rerun()




def login_page():
    st.title("Log In to AOPL PathPoint")

    # Connect to Google Sheets
    sheet = connect_to_gsheet("PathPoint_Streemlit_Version")
    users_sheet = sheet.worksheet("Users") if sheet else None

    st.markdown("#### Please enter your credentials to log in:")

    # Input fields for login
    email = st.text_input("✉️ Email", placeholder="Enter your registered email")
    staff_id = st.text_input("🆔 Staff ID", placeholder="Enter your staff ID", type="password")

    if st.button("Log In"):
        if not email or not staff_id:
            st.error("Both email and staff ID are required.")
        else:
            if users_sheet:
                try:
                    # Fetch all user records
                    records = users_sheet.get_all_records()

                    # Validate email and staff ID
                    user = next(
                        (
                            record
                            for record in records
                            if str(record.get("Email", "")).strip().lower() == email.strip().lower()
                            and str(record.get("Staff ID", "")).strip() == staff_id.strip()
                        ),
                        None,
                    )

                    if user:
                        # Successful login
                        st.session_state["user_email"] = email
                        st.session_state["user_name"] = user.get("Full Name", "User")
                        st.session_state["staff_id"] = staff_id
                        st.success(f"Welcome, {st.session_state['user_name']}!")

                        # Force navigation to Visit Form
                        st.rerun()
                    else:
                        st.error("Invalid email or staff ID. Please try again.")
                except Exception as e:
                    st.error(f"Error during validation: {e}")
            else:
                st.error("Unable to connect to the Users database.")









# Attendance Page
def attendance_page():
    st.title("Attendance")

    # Retrieve email from session state or prompt user
    email = st.session_state.get("user_email", "")
    if email:
        st.info(f"Logged in as: {email}")
    else:
        email = st.text_input("✉️ Enter Your Email Address", placeholder="Enter your email address")
        if not email:
            st.error("Please enter your email to proceed.")
            return

    # Google Sheets connection
    sheet = connect_to_gsheet("PathPoint_Streemlit_Version")
    attendance_sheet = sheet.worksheet("Attendance") if sheet else None

    if not attendance_sheet:
        st.error("Unable to connect to the Attendance database.")
        return

    # Attendance options
    leave_type = st.radio("Attendance Type", ["Start Work", "End Work", "Leave"], index=0)

    # Initialize placeholders
    start_time = "N/A"
    end_time = "N/A"
    start_date = "N/A"
    end_date = "N/A"
    day_count = "N/A"
    leave_half = "N/A"
    work_status = leave_type

    # Handle "Start Work"
    if leave_type == "Start Work":
        st.subheader("Start Work")
        start_time = datetime.now().strftime("%I:%M %p")
        st.write(f"**Start Time:** {start_time}")
        work_status = "Present"

    # Handle "End Work"
    elif leave_type == "End Work":
        st.subheader("End Work")
        end_time = datetime.now().strftime("%I:%M %p")
        st.write(f"**End Time:** {end_time}")

        # Check for a valid "Start Work" entry for the day
        today_date = datetime.now().strftime("%Y-%m-%d")
        attendance_records = attendance_sheet.get_all_records()
        matching_record = next(
            (record for record in attendance_records if record["User Email"] == email and 
             record["Date"].startswith(today_date) and record["Work Status"] == "Present"),
            None
        )

        if not matching_record:
            st.error("No 'Start Work' entry found for today. Please record 'Start Work' first.")
            return

    # Handle "Leave"
    elif leave_type == "Leave":
        leave_sub_type = st.radio("Leave Type", ["Full Day Leave", "Half Day Leave"], index=0)

        if leave_sub_type == "Full Day Leave":
            start_date = st.date_input("Start Date")
            end_date = st.date_input("End Date")
            if start_date > end_date:
                st.error("Start Date cannot be after End Date.")
                return
            day_count = (end_date - start_date).days + 1
            st.write(f"**Total Days:** {day_count} days")

        elif leave_sub_type == "Half Day Leave":
            leave_half = st.radio(
                "Choose Half Day",
                ["First Half (09:00 AM - 01:00 PM)", "Second Half (01:00 PM - 05:00 PM)"]
            )
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = start_date
            day_count = 0.5

        work_status = leave_sub_type

    # Submit Attendance
    if st.button("Submit Attendance"):
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        unique_id = str(uuid.uuid4())

        # Convert start_date and end_date to string before appending to Google Sheets
        start_date_str = start_date if isinstance(start_date, str) else start_date.strftime("%Y-%m-%d")
        end_date_str = end_date if isinstance(end_date, str) else end_date.strftime("%Y-%m-%d")

        # Record "Start Work"
        if leave_type == "Start Work":
            attendance_sheet.append_row([date, unique_id, email, start_time, end_time, work_status, 
                                         start_date_str, end_date_str, day_count, leave_half])
            st.success("Start Work recorded successfully!")

        # Update "End Work"
        elif leave_type == "End Work" and matching_record:
            record_index = attendance_records.index(matching_record) + 2
            attendance_sheet.update_cell(record_index, 5, end_time)  # Update End Time
            st.success("End Work recorded successfully!")

        # Record Leave
        elif leave_type == "Leave":
            attendance_sheet.append_row([date, unique_id, email, start_time, end_time, work_status, 
                                         start_date_str, end_date_str, day_count, leave_half])
            st.success(f"{leave_type} recorded successfully!")





# Vist Form
def visit_form_page():
    st.title("Provide Visit Information")

    # Retrieve email from session state
    email = st.session_state.get("user_email", "")
    
    if email:
        st.info(f"Logged in as: {email}")
    else:
        email = st.text_input("Enter your email", placeholder="Enter your email")
        if not email:
            st.warning("Please enter your email to proceed.")
            return

    # Visit Type selection
    visit_type = st.selectbox("Visit Type", ["Dealer Visit", "Retailer Visit", "Building Visit", "Plumber Visit"])

    # Form inputs
    name = st.text_input("Name", placeholder="Enter your name")
    code = st.text_input("Code/Number", placeholder="Enter a valid code")
    aopl_value = st.number_input("AOPL Collection Value", min_value=0, step=1)
    agl_value = st.number_input("AGL Collection Value", min_value=0, step=1)
    pump_value = st.number_input("Pump Collection Value", min_value=0, step=1)
    total_so_value = st.number_input("Total SO", min_value=0, step=1)
    feedback = st.text_area("Feedback", placeholder="Enter any additional feedback")

    # Calculate total collection value
    total_value = aopl_value + agl_value + pump_value
    st.write(f"**Total Collection Value:** {total_value}")

    # Image upload for Memo and Visit Picture
    memo_picture = st.file_uploader("Upload Memo Picture", type=["jpg", "png", "jpeg"])
    #visit_picture = st.file_uploader("Upload Visit Picture", type=["jpg", "png", "jpeg"])

    # Automatic location retrieval with fallback
    try:
        geolocator = Nominatim(user_agent="AOPL PathPoint")
        location = geolocator.geocode("Bangladesh")  # Replace with dynamic location if available
        if location:
            latitude, longitude = location.latitude, location.longitude
        else:
            latitude, longitude = "N/A", "N/A"
    except Exception as e:
        st.warning("Geolocation failed. Please manually input your location.")
        latitude, longitude = "N/A", "N/A"

    # Manual location input if geolocation fails
    if latitude == "N/A" or longitude == "N/A":
        latitude = st.text_input("Latitude", value="N/A")
        longitude = st.text_input("Longitude", value="N/A")

    # Function to simulate file upload to Google Drive (stub method - replace with actual logic)
    def upload_to_google_drive(file):
        if file:
            # Simulate upload success and return mock URL
            return f"https://drive.google.com/your_uploaded_file/{file.name}"
        return "N/A"

    # Upload memo and visit pictures to Google Drive and get URLs
    memo_url = upload_to_google_drive(memo_picture)
    #visit_picture_url = upload_to_google_drive(visit_picture)

    # Submit button logic
    if st.button("Submit"):
        if not name or not code:
            st.error("Please fill out all required fields: Name and Code.")
            return
        
        # Unique ID and timestamp
        unique_id = str(uuid.uuid4())
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Connect to Google Sheets
        sheet = connect_to_gsheet("PathPoint_Streemlit_Version")
        visit_sheet = sheet.worksheet("Visit_Details") if sheet else None

        if visit_sheet:
            # Append data to Google Sheets
            visit_sheet.append_row([date, unique_id, email, latitude, longitude, visit_type, name, code,
                                    aopl_value, agl_value, pump_value, total_so_value, total_value, feedback,
                                    memo_url])
            st.success("Form submitted successfully!")
        else:
            st.error("Error submitting data. Please try again.")







#visit_history_page

def visit_history_page():
    st.title("Visit History")

    # Dynamic email retrieval
    email = st.text_input("Enter your email", placeholder="Enter your email to view your visit history")

    # Date selection for filtering history
    selected_date = st.date_input("Select a Date", value=datetime.now().date())

    if not email:
        st.warning("Please enter your email to view visit history.")
        return

    # Connect to Google Sheets
    sheet = connect_to_gsheet()

    # Define the expected headers for the Google Sheet
    expected_headers = [
        "Date of Entry", "Unique ID", "User Email", "Latitude", "Longitude",
        "Visit Type", "Name", "Code/Number", "AOPL Collection Value",
        "AGL Collection Value", "Pump Collection Value", "Total SO Value",
        "Total Collection Value", "Feedback", "Memo Picture URL", "Visit Picture URL"
    ]

    try:
        # Fetch all records from the sheet
        visit_records = sheet.sheet1.get_all_records(expected_headers=expected_headers) if sheet else []
    except Exception as e:
        st.error(f"Error fetching data from Google Sheets: {e}")
        return

    # Filter records for the selected user and date
    filtered_records = [
        record for record in visit_records
        if record["User Email"] == email and record["Date of Entry"].startswith(str(selected_date))
    ]

    if not filtered_records:
        st.warning(f"No visit history found for {selected_date.strftime('%Y-%m-%d')}.")
        return

    # Convert filtered records to a DataFrame
    df = pd.DataFrame(filtered_records)

    # Rename columns for a cleaner UI
    df.rename(columns={
        "Date of Entry": "Date",
        "User Email": "Email",
        "Code/Number": "Code",
        "AOPL Collection Value": "AOPL Collection",
        "AGL Collection Value": "AGL Collection",
        "Pump Collection Value": "Pump Collection",
        "Total SO Value": "Total SO",
        "Total Collection Value": "Total Collection",
    }, inplace=True)

    # Format numeric columns for better readability
    numeric_columns = ["AOPL Collection", "AGL Collection", "Pump Collection", "Total SO", "Total Collection"]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0).astype(float)

    # Keep only relevant columns for display
    columns_to_display = ["Visit Type", "Name", "Code", "AOPL Collection", "AGL Collection", "Pump Collection", "Total SO", "Total Collection", "Feedback"]
    display_df = df[columns_to_display]

    # Display the filtered visit history
    st.subheader(f"Visit History for {selected_date.strftime('%Y-%m-%d')}")
    st.dataframe(display_df.style.format({
        "AOPL Collection": "BDT {:.2f}",
        "AGL Collection": "BDT {:.2f}",
        "Pump Collection": "BDT {:.2f}",
        "Total SO": "BDT {:.2f}",
        "Total Collection": "BDT {:.2f}",
    }))

    # Add option to download the visit history as a CSV
    csv_data = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Visit History as CSV",
        data=csv_data,
        file_name=f"visit_history_{selected_date.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )







 

def home_page():
    # Customizing the title and description
    st.markdown(
        '''
        <style>
            .title {
                font-size: 40px;
                font-weight: bold;
                color: #1E3D58;
                text-align: center;
                padding: 20px;
            }
            .description {
                font-size: 20px;
                color: #666;
                text-align: center;
                margin-bottom: 50px;
            }
            .button-container {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-top: 20px;
            }
            .button-container button {
                padding: 15px 25px;
                background-color: #1E3D58;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 18px;
                cursor: pointer;
            }
            .button-container button:hover {
                background-color: #0C2747;
            }
        </style>
        ''', unsafe_allow_html=True)

    st.markdown('<div class="title">Welcome to AOPL PathPoint</div>', unsafe_allow_html=True)
    st.markdown('<div class="description">An easy-to-use platform for efficient visit tracking and management</div>', unsafe_allow_html=True)

    # Button navigation layout
    st.markdown(
        '''
        <div class="button-container">
            <button onclick="window.location.href='http://192.168.103.55:8502/'">Visit Form</button>
            <button onclick="window.location.href='/Registration Form'">Registration Form</button>
            <button onclick="window.location.href='/Attendance'">Attendance</button>
            <button onclick="window.location.href='/Visit History'">Visit History</button>
        </div>
        ''', unsafe_allow_html=True)



def main():
    st.sidebar.title("AOPL PathPoint")
    
    # Check if user is logged in
    if "user_email" not in st.session_state:
        # Redirect to login or registration
        login_or_register = st.sidebar.radio("Choose an option", ["Log In", "Register"])
        if login_or_register == "Log In":
            login_page()
        elif login_or_register == "Register":
            registration_page()
    else:
        # Show app features after login
        st.sidebar.success(f"Logged in as: {st.session_state['user_name']}")
        selection = st.sidebar.radio("Go to", ["Visit Form", "Attendance", "Visit History", "Log Out"])

        if selection == "Visit Form":
            visit_form_page()
        elif selection == "Attendance":
            attendance_page()
        elif selection == "Visit History":
            visit_history_page()
        elif selection == "Log Out":
            # Clear session state and reload
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()

