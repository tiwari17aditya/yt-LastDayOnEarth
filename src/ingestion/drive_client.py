"""Google Drive API client strictly constrained to MyDrive -> youtube-projects -> LastDayOnEarth."""

import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials

from src.logging_config import get_logger
from src.exceptions import IngestionError
from src.google_auth import get_google_credentials

logger = get_logger(component="DriveIngestion")

# Strict safety path constants
ALLOWED_PARENT_FOLDER = "youtube-projects"
ALLOWED_PROJECT_FOLDER = "LastDayOnEarth"
DEFAULT_INPUT_FOLDER = "Input"
DEFAULT_PROCESSED_FOLDER = "Processed"
DEFAULT_OUTPUT_FOLDER = "Output"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


class BaseIngestionClient(ABC):
    """Abstract interface for video ingestion clients."""

    @abstractmethod
    def list_pending_videos(self) -> List[Dict[str, Any]]:
        """List video files ready for processing."""
        pass

    @abstractmethod
    def download_video(self, file_id: str, destination_path: Path) -> Path:
        """Download remote video file to local filesystem."""
        pass

    @abstractmethod
    def mark_as_processed(self, file_id: str) -> None:
        """Move or tag the video file in remote storage as processed."""
        pass


class GoogleDriveClient(BaseIngestionClient):
    """Google Drive API v3 client with strict folder-boundary isolation.
    
    SAFETY RULE: NEVER touches or lists any folder/file outside:
    MyDrive -> youtube-projects -> LastDayOnEarth -> (Input | Processed | Output)
    """

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        input_folder_name: str = DEFAULT_INPUT_FOLDER,
        processed_folder_name: str = DEFAULT_PROCESSED_FOLDER,
        output_folder_name: str = DEFAULT_OUTPUT_FOLDER,
    ) -> None:
        self.credentials = credentials
        self.input_folder_name = input_folder_name
        self.processed_folder_name = processed_folder_name
        self.output_folder_name = output_folder_name
        self.service = None

        # Resolved Drive folder IDs (Strictly locked to project boundaries)
        self.project_root_id: Optional[str] = None
        self.input_folder_id: Optional[str] = None
        self.processed_folder_id: Optional[str] = None
        self.output_folder_id: Optional[str] = None

    def connect(self) -> None:
        """Connects to Google Drive API and verifies strict folder hierarchy."""
        try:
            if not self.credentials:
                self.credentials = get_google_credentials(
                    scopes=["https://www.googleapis.com/auth/drive"]
                )

            if not self.credentials:
                raise IngestionError(
                    operation="connect",
                    root_cause="Missing Google Drive credentials.",
                    recovery_action="Run scripts/setup_google_auth.py or configure GCP_REFRESH_TOKEN in .env/secrets.",
                )

            self.service = build("drive", "v3", credentials=self.credentials, cache_discovery=False)
            logger.info("Successfully established connection to Google Drive API v3")

            # Resolve strict folder boundaries
            self._resolve_safety_folders()

        except IngestionError:
            raise
        except Exception as e:
            raise IngestionError(
                operation="connect",
                root_cause=str(e),
                recovery_action="Ensure Drive API is enabled in Google Cloud Console and credentials have 'drive' scope.",
            )

    def _find_single_folder(self, name: str, parent_id: str = "root") -> Optional[str]:
        """Finds a child folder with exact name and parent. Safe read-only search."""
        query = (
            f"name = '{name}' and '{parent_id}' in parents and "
            f"mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
        response = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=10,
        ).execute()

        files = response.get("files", [])
        if files:
            return files[0]["id"]
        return None

    def _ensure_folder(self, name: str, parent_id: str) -> str:
        """Finds an existing folder or creates it strictly within the specified parent."""
        existing_id = self._find_single_folder(name, parent_id)
        if existing_id:
            return existing_id

        logger.info(f"Creating project folder '{name}' inside parent {parent_id}")
        file_metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = self.service.files().create(body=file_metadata, fields="id").execute()
        return folder["id"]

    def _resolve_safety_folders(self) -> None:
        """Enforces the strict path: MyDrive -> youtube-projects -> LastDayOnEarth -> (Input & Processed).
        
        Refuses to proceed if the project path is violated.
        """
        logger.info(f"Locating Drive path: MyDrive -> {ALLOWED_PARENT_FOLDER} -> {ALLOWED_PROJECT_FOLDER}")

        # 1. Locate youtube-projects in MyDrive (root)
        youtube_projects_id = self._find_single_folder(ALLOWED_PARENT_FOLDER, parent_id="root")
        if not youtube_projects_id:
            raise IngestionError(
                operation="resolve_folders",
                root_cause=f"Parent folder '{ALLOWED_PARENT_FOLDER}' not found in MyDrive.",
                recovery_action=f"Create folder '{ALLOWED_PARENT_FOLDER}' in your Google Drive root.",
            )

        # 2. Locate LastDayOnEarth inside youtube-projects
        self.project_root_id = self._find_single_folder(ALLOWED_PROJECT_FOLDER, parent_id=youtube_projects_id)
        if not self.project_root_id:
            raise IngestionError(
                operation="resolve_folders",
                root_cause=f"Project folder '{ALLOWED_PROJECT_FOLDER}' not found in '{ALLOWED_PARENT_FOLDER}'.",
                recovery_action=f"Create folder '{ALLOWED_PROJECT_FOLDER}' inside '{ALLOWED_PARENT_FOLDER}' in Google Drive.",
            )

        # 3. Locate or create Input, Processed, and Output inside LastDayOnEarth
        self.input_folder_id = self._ensure_folder(self.input_folder_name, parent_id=self.project_root_id)
        self.processed_folder_id = self._ensure_folder(self.processed_folder_name, parent_id=self.project_root_id)
        self.output_folder_id = self._ensure_folder(self.output_folder_name, parent_id=self.project_root_id)

        logger.info(
            "Drive folder boundaries locked successfully",
            extra_data={
                "project_root_id": self.project_root_id,
                "input_folder_id": self.input_folder_id,
                "processed_folder_id": self.processed_folder_id,
                "output_folder_id": self.output_folder_id,
            },
        )

    def list_pending_videos(self) -> List[Dict[str, Any]]:
        """Strictly queries only the Input folder for video recordings."""
        if not self.service or not self.input_folder_id:
            self.connect()

        logger.info("Scanning Drive Input folder for pending recordings", extra_data={"folder_id": self.input_folder_id})
        
        # Strict isolation: Query restricted ONLY to input_folder_id
        query = (
            f"'{self.input_folder_id}' in parents and trashed = false and "
            f"mimeType != 'application/vnd.google-apps.folder'"
        )

        try:
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, size, mimeType, md5Checksum, createdTime)",
                pageSize=50,
                orderBy="createdTime",
            ).execute()

            files = results.get("files", [])
            if not files:
                return []

            # Retrieve checksums of already processed videos to prevent duplicate processing
            processed_md5s = set()
            try:
                proc_query = f"'{self.processed_folder_id}' in parents and trashed = false"
                proc_results = self.service.files().list(
                    q=proc_query,
                    spaces="drive",
                    fields="files(id, name, md5Checksum)",
                    pageSize=100,
                ).execute()
                for pf in proc_results.get("files", []):
                    if pf.get("md5Checksum"):
                        processed_md5s.add(pf["md5Checksum"])
            except Exception as pe:
                logger.warning(f"Could not scan processed folder for MD5s: {pe}")

            pending_videos = []
            seen_input_md5s = set()

            for f in files:
                name = f.get("name", "")
                file_id = f.get("id")
                suffix = Path(name).suffix.lower()
                mime = f.get("mimeType", "")
                md5 = f.get("md5Checksum")

                if suffix in VIDEO_EXTENSIONS or mime.startswith("video/"):
                    # Check 1: Duplicate of an already processed recording
                    if md5 and md5 in processed_md5s:
                        logger.warning(
                            f"Input video '{name}' (MD5: {md5}) is a duplicate of an already processed file. "
                            f"Auto-moving directly to Processed folder."
                        )
                        self.mark_as_processed(file_id)
                        continue

                    # Check 2: Duplicate twin inside the same Input folder
                    if md5 and md5 in seen_input_md5s:
                        logger.warning(
                            f"Input video '{name}' is a duplicate of another file in Input. "
                            f"Archiving duplicate to Processed folder."
                        )
                        self.mark_as_processed(file_id)
                        continue

                    if md5:
                        seen_input_md5s.add(md5)

                    pending_videos.append({
                        "id": file_id,
                        "name": name,
                        "size": int(f.get("size", 0)),
                        "createdTime": f.get("createdTime"),
                        "md5Checksum": md5,
                    })

            logger.info(f"Found {len(pending_videos)} pending video(s) in Drive Input folder (after deduplication)")
            return pending_videos

        except Exception as e:
            raise IngestionError(
                operation="list_pending_videos",
                root_cause=str(e),
                recovery_action="Check Drive API quota and folder permissions.",
            )

    def download_video(self, file_id: str, destination_path: Path) -> Path:
        """Downloads a video file chunk-by-chunk with streaming to conserve memory."""
        if not self.service:
            self.connect()

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading video ({file_id}) to {destination_path}")

        try:
            request = self.service.files().get_media(fileId=file_id)
            with io.FileIO(destination_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=20 * 1024 * 1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Download progress: {int(status.progress() * 100)}%")

            logger.info(f"Download complete: {destination_path} ({destination_path.stat().st_size} bytes)")
            return destination_path

        except Exception as e:
            if destination_path.exists():
                destination_path.unlink()
            raise IngestionError(
                operation="download_video",
                root_cause=str(e),
                recovery_action="Verify network stability and available disk space.",
                file_path=str(destination_path),
            )

    def mark_as_processed(self, file_id: str) -> None:
        """Moves video file from Input folder to Processed folder strictly within LastDayOnEarth."""
        if not self.service or not self.input_folder_id or not self.processed_folder_id:
            self.connect()

        logger.info(f"Moving file {file_id} from Input to Processed folder in Drive")
        try:
            # Move file by updating parent folders
            updated = self.service.files().update(
                fileId=file_id,
                addParents=self.processed_folder_id,
                removeParents=self.input_folder_id,
                fields="id, parents",
            ).execute()

            # Strict removal verification: guarantee input_folder_id is no longer a parent
            parents = updated.get("parents", [])
            if self.input_folder_id in parents:
                logger.warning(f"File {file_id} still associated with Input folder. Enforcing removal.")
                self.service.files().update(
                    fileId=file_id,
                    removeParents=self.input_folder_id,
                    fields="id, parents",
                ).execute()

            logger.info(f"File {file_id} successfully archived in Processed folder and removed from Input.")
        except Exception as e:
            raise IngestionError(
                operation="mark_as_processed",
                root_cause=str(e),
                recovery_action="Check file permissions in Google Drive.",
            )

    def delete_video(self, file_id: str) -> None:
        """Deletes processed raw video from Google Drive permanently (or trashes if delete is restricted)."""
        if not self.service:
            self.connect()

        logger.info(f"Deleting raw video {file_id} from Google Drive")
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"Video {file_id} permanently deleted from Google Drive Input.")
        except Exception as e:
            logger.warning(f"Permanent deletion failed for file {file_id}: {e}. Attempting to trash...")
            try:
                self.service.files().update(fileId=file_id, body={"trashed": True}).execute()
                logger.info(f"Video {file_id} successfully trashed in Google Drive.")
            except Exception as te:
                raise IngestionError(
                    operation="delete_video",
                    root_cause=f"Delete failed: {e}; Trash failed: {te}",
                    recovery_action="Check file ownership and delete permissions in Google Drive.",
                )

    def upload_processed_video(
        self,
        local_video_path: Path,
        metadata_path: Optional[Path] = None,
        processing_date: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Uploads the processed video and metadata to Drive Output organized by Year -> Month -> video_ddmmyyyy."""
        if not self.service or not self.output_folder_id:
            self.connect()

        from datetime import datetime
        from googleapiclient.http import MediaFileUpload

        date = processing_date or datetime.now()
        year_str = date.strftime("%Y")
        month_str = date.strftime("%m")
        ddmmyyyy = date.strftime("%d%m%Y")

        # 1. Structure: Output -> videos -> Year -> Month
        videos_root_id = self._ensure_folder("videos", parent_id=self.output_folder_id)
        video_year_id = self._ensure_folder(year_str, parent_id=videos_root_id)
        video_month_id = self._ensure_folder(month_str, parent_id=video_year_id)

        # 2. Structure: Output -> metadata -> Year -> Month
        metadata_root_id = self._ensure_folder("metadata", parent_id=self.output_folder_id)
        meta_year_id = self._ensure_folder(year_str, parent_id=metadata_root_id)
        meta_month_id = self._ensure_folder(month_str, parent_id=meta_year_id)

        # Check existing filenames in destination to prevent duplicate collisions
        existing_vids = set()
        try:
            q_vids = f"'{video_month_id}' in parents and trashed = false"
            res_vids = self.service.files().list(q=q_vids, spaces="drive", fields="files(name)").execute()
            existing_vids = {f["name"] for f in res_vids.get("files", [])}
        except Exception as e:
            logger.warning(f"Could not list existing video files for collision check: {e}")

        # 3. Filename formats: video_ddmmyyyy.mp4 and metadata_ddmmyyyy.json (auto-disambiguated)
        drive_video_name = f"video_{ddmmyyyy}.mp4"
        meta_name = f"metadata_{ddmmyyyy}.json"

        if drive_video_name in existing_vids:
            counter = 1
            while f"video_{ddmmyyyy}_{counter}.mp4" in existing_vids:
                counter += 1
            drive_video_name = f"video_{ddmmyyyy}_{counter}.mp4"
            meta_name = f"metadata_{ddmmyyyy}_{counter}.json"
            logger.info(f"Resolved Drive output collision: disambiguated filename to {drive_video_name}")

        logger.info(
            f"Uploading processed video to Drive Output/videos/{year_str}/{month_str}/{drive_video_name}",
            extra_data={"local_path": str(local_video_path)},
        )

        try:
            media = MediaFileUpload(
                str(local_video_path),
                mimetype="video/mp4",
                chunksize=20 * 1024 * 1024,
                resumable=True,
            )

            file_metadata = {
                "name": drive_video_name,
                "parents": [video_month_id],
            }

            request = self.service.files().create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Drive output video upload progress: {int(status.progress() * 100)}%")

            uploaded_video_id = response.get("id")
            logger.info(f"Successfully uploaded video to Drive Output: {drive_video_name} (ID: {uploaded_video_id})")

            # 4. Upload companion metadata JSON into Output/metadata/year/month/
            uploaded_meta_id = None
            if metadata_path and metadata_path.exists():
                meta_media = MediaFileUpload(str(metadata_path), mimetype="application/json")
                meta_request = self.service.files().create(
                    body={"name": meta_name, "parents": [meta_month_id]},
                    media_body=meta_media,
                    fields="id, name",
                )
                meta_resp = meta_request.execute()
                uploaded_meta_id = meta_resp.get("id")
                logger.info(f"Uploaded metadata JSON to Drive Output/metadata/{year_str}/{month_str}/{meta_name}")

            return {
                "video_id": uploaded_video_id,
                "video_name": drive_video_name,
                "video_folder": f"Output/videos/{year_str}/{month_str}",
                "metadata_id": uploaded_meta_id,
                "metadata_name": meta_name if uploaded_meta_id else None,
                "metadata_folder": f"Output/metadata/{year_str}/{month_str}",
            }
        except Exception as e:
            logger.error(f"Failed to upload processed video to Google Drive Output: {e}")
            raise IngestionError(
                operation="upload_processed_video",
                root_cause=str(e),
                recovery_action="Check Google Drive storage quota and folder permissions.",
                file_path=str(local_video_path),
            )
