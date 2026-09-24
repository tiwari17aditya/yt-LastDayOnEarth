"""Helper to move the raw video from Processed back to Input for live end-to-end testing."""

from src.ingestion.drive_client import GoogleDriveClient

client = GoogleDriveClient()
client.connect()

query = f"'{client.processed_folder_id}' in parents and trashed = false"
res = client.service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
files = res.get("files", [])

if files:
    target_file = files[0]
    file_id = target_file["id"]
    file_name = target_file["name"]
    print(f"Staging '{file_name}' ({file_id}) into Input folder...")
    client.service.files().update(
        fileId=file_id,
        addParents=client.input_folder_id,
        removeParents=client.processed_folder_id,
        fields="id, parents",
    ).execute()
    print("Video successfully placed in Input for test run!")
else:
    print("No files found in Processed.")
