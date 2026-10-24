"""Google Drive API client strictly constrained to MyDrive -> youtube-projects -> LastDayOnEarth."""

import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
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
DEFAULT_ASSETS_FOLDER = "Assets"

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
    MyDrive -> youtube-projects -> LastDayOnEarth -> (Input | Processed | Output | Assets)
    """

    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        input_folder_name: str = DEFAULT_INPUT_FOLDER,
        processed_folder_name: str = DEFAULT_PROCESSED_FOLDER,
        output_folder_name: str = DEFAULT_OUTPUT_FOLDER,
        assets_folder_name: str = DEFAULT_ASSETS_FOLDER,
    ) -> None:
        self.credentials = credentials
        self.input_folder_name = input_folder_name
        self.processed_folder_name = processed_folder_name
        self.output_folder_name = output_folder_name
        self.assets_folder_name = assets_folder_name
        self.service = None

        # Resolved Drive folder IDs (Strictly locked to project boundaries)
        self.project_root_id: Optional[str] = None
        self.input_folder_id: Optional[str] = None
        self.processed_folder_id: Optional[str] = None
        self.output_folder_id: Optional[str] = None
        self.assets_folder_id: Optional[str] = None

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

        # 3. Locate or create Input, Processed, Output, and Assets inside LastDayOnEarth
        self.input_folder_id = self._ensure_folder(self.input_folder_name, parent_id=self.project_root_id)
        self.processed_folder_id = self._ensure_folder(self.processed_folder_name, parent_id=self.project_root_id)
        self.output_folder_id = self._ensure_folder(self.output_folder_name, parent_id=self.project_root_id)
        self.assets_folder_id = self._ensure_folder(self.assets_folder_name, parent_id=self.project_root_id)

        logger.info(
            "Drive folder boundaries locked successfully",
            extra_data={
                "project_root_id": self.project_root_id,
                "input_folder_id": self.input_folder_id,
                "processed_folder_id": self.processed_folder_id,
                "output_folder_id": self.output_folder_id,
                "assets_folder_id": self.assets_folder_id,
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
                    size_bytes = int(f.get("size", 0))

                    # Edge Case 1: Empty or 0-byte placeholder files
                    if size_bytes < 1024:
                        logger.warning(
                            f"Skipping file '{name}' ({file_id}) in Input: size is too small ({size_bytes} bytes). "
                            f"Likely empty placeholder or incomplete creation."
                        )
                        continue

                    # Edge Case 2: Upload in progress on Google Drive
                    if "md5Checksum" in f and not md5 and size_bytes > 0:
                        logger.info(
                            f"Skipping file '{name}' ({file_id}) in Input: MD5 checksum not yet finalized by Drive (upload in progress). "
                            f"Will automatically process once upload completes."
                        )
                        continue

                    # Check 1: Duplicate of an already processed recording
                    if md5 and md5 in processed_md5s:
                        logger.warning(
                            f"Input video '{name}' (MD5: {md5}) is a duplicate of an already processed file. "
                            f"Auto-deleting duplicate directly from Input."
                        )
                        self.delete_video(file_id)
                        continue

                    # Check 2: Duplicate twin inside the same Input folder
                    if md5 and md5 in seen_input_md5s:
                        logger.warning(
                            f"Input video '{name}' is a duplicate twin of another file in Input. "
                            f"Auto-deleting duplicate directly from Input."
                        )
                        self.delete_video(file_id)
                        continue

                    if md5:
                        seen_input_md5s.add(md5)

                    pending_videos.append({
                        "id": file_id,
                        "name": name,
                        "size": size_bytes,
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

            if not destination_path.exists() or destination_path.stat().st_size == 0:
                if destination_path.exists():
                    destination_path.unlink()
                raise IngestionError(
                    operation="download_video",
                    root_cause="Downloaded video file is 0 bytes or empty.",
                    recovery_action="Check source file on Google Drive and network connection.",
                    file_path=str(destination_path),
                )

            logger.info(f"Download complete: {destination_path} ({destination_path.stat().st_size} bytes)")
            return destination_path

        except Exception as e:
            if destination_path.exists():
                destination_path.unlink()
            if isinstance(e, IngestionError):
                raise e
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

    def cleanup_processed_folder(self) -> int:
        """Purges all files from the Drive Processed folder.
        
        Since videos are tracked by file ID/checksum and history tracker,
        the Processed directory is cleared daily to conserve cloud storage.
        """
        if not self.service or not self.processed_folder_id:
            self.connect()

        logger.info("Initiating cleanup of Drive Processed folder", extra_data={"folder_id": self.processed_folder_id})
        query = f"'{self.processed_folder_id}' in parents and trashed = false"
        deleted_count = 0

        try:
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType)",
                pageSize=100,
            ).execute()

            files = results.get("files", [])
            for f in files:
                file_id = f.get("id")
                file_name = f.get("name")
                logger.info(f"Purging file from Drive Processed folder: {file_name} ({file_id})")
                try:
                    self.delete_video(file_id)
                    deleted_count += 1
                except Exception as de:
                    logger.warning(f"Could not delete processed file {file_name} ({file_id}): {de}")

            logger.info(f"Processed folder cleanup complete: removed {deleted_count} file(s).")
            return deleted_count
        except Exception as e:
            logger.warning(f"Failed to query files for Processed folder cleanup: {e}")
            return deleted_count

    def cleanup_old_output_videos(self, retention_days: int = 7) -> int:
        """Deletes video files from Google Drive Output folder older than retention_days (default: 7 days)."""
        if not self.service or not self.output_folder_id:
            self.connect()

        from datetime import datetime, timezone, timedelta
        cutoff_dt = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff_iso = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        logger.info(
            f"Scanning Drive Output folder for videos older than {retention_days} days (cutoff: {cutoff_iso})",
            extra_data={"output_folder_id": self.output_folder_id, "retention_days": retention_days},
        )

        deleted_count = 0

        def _purge_old_videos_in_folder(folder_id: str) -> None:
            nonlocal deleted_count
            q = (
                f"'{folder_id}' in parents and trashed = false and "
                f"mimeType != 'application/vnd.google-apps.folder'"
            )
            try:
                res = self.service.files().list(
                    q=q,
                    spaces="drive",
                    fields="files(id, name, mimeType, createdTime)",
                    pageSize=100,
                ).execute()
                for item in res.get("files", []):
                    name = item.get("name", "")
                    fid = item.get("id")
                    suffix = Path(name).suffix.lower()
                    mime = item.get("mimeType", "")
                    created_time_str = item.get("createdTime")

                    if suffix in VIDEO_EXTENSIONS or mime.startswith("video/"):
                        is_old = False
                        if created_time_str:
                            try:
                                dt_parsed = datetime.fromisoformat(created_time_str.replace("Z", "+00:00"))
                                if dt_parsed < cutoff_dt:
                                    is_old = True
                            except Exception:
                                pass

                        if not is_old and "video_" in name:
                            try:
                                date_part = name.split("video_")[1].split(".")[0].split("_")[0]
                                dt_from_name = datetime.strptime(date_part, "%d%m%Y").replace(tzinfo=timezone.utc)
                                if dt_from_name < cutoff_dt:
                                    is_old = True
                            except Exception:
                                pass

                        if is_old:
                            logger.info(
                                f"Deleting expired output video (> {retention_days} days): {name} ({fid}, created: {created_time_str})"
                            )
                            try:
                                self.delete_video(fid)
                                deleted_count += 1
                            except Exception as de:
                                logger.warning(f"Could not delete expired output video {name} ({fid}): {de}")
            except Exception as e:
                logger.warning(f"Could not scan folder {folder_id} for output videos: {e}")

        try:
            # 1. Check Output/videos/ root
            videos_root_id = self._find_single_folder("videos", parent_id=self.output_folder_id)
            if videos_root_id:
                q_years = f"'{videos_root_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                res_years = self.service.files().list(q=q_years, spaces="drive", fields="files(id, name)").execute()
                for yf in res_years.get("files", []):
                    q_months = f"'{yf['id']}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
                    res_months = self.service.files().list(q=q_months, spaces="drive", fields="files(id, name)").execute()
                    for mf in res_months.get("files", []):
                        _purge_old_videos_in_folder(mf["id"])

                _purge_old_videos_in_folder(videos_root_id)

            # 2. Also check direct files in output_folder_id
            _purge_old_videos_in_folder(self.output_folder_id)

            logger.info(f"Drive Output retention cleanup complete: deleted {deleted_count} video(s).")
            return deleted_count

        except Exception as e:
            logger.warning(f"Error executing Drive Output retention cleanup: {e}")
            return deleted_count

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

    def download_file_by_id(self, file_id: str, destination_path: Path) -> Path:
        """Downloads any remote Google Drive file chunk-by-chunk to destination_path."""
        if not self.service:
            self.connect()

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Downloading Drive asset ({file_id}) to {destination_path}")

        try:
            request = self.service.files().get_media(fileId=file_id)
            with io.FileIO(destination_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=10 * 1024 * 1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        logger.info(f"Asset download progress ({destination_path.name}): {int(status.progress() * 100)}%")

            if not destination_path.exists() or destination_path.stat().st_size == 0:
                if destination_path.exists():
                    destination_path.unlink()
                raise IngestionError(
                    operation="download_file_by_id",
                    root_cause="Downloaded asset is 0 bytes or empty.",
                    recovery_action="Check source asset on Google Drive and network connectivity.",
                    file_path=str(destination_path),
                )

            logger.info(f"Asset downloaded successfully: {destination_path} ({destination_path.stat().st_size} bytes)")
            return destination_path
        except Exception as e:
            if destination_path.exists():
                destination_path.unlink()
            if isinstance(e, IngestionError):
                raise
            raise IngestionError(
                operation="download_file_by_id",
                root_cause=str(e),
                recovery_action="Verify Drive permissions and network connection.",
                file_path=str(destination_path),
            )

    def upload_static_asset(
        self,
        local_path: Path,
        subfolder_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Uploads a static asset (video, image, audio) into Drive Assets or a subfolder within Assets."""
        if not self.service or not self.assets_folder_id:
            self.connect()

        if not local_path.exists():
            raise IngestionError(
                operation="upload_static_asset",
                root_cause=f"Local asset file not found: {local_path}",
                recovery_action="Verify the local file exists before uploading.",
                file_path=str(local_path),
            )

        target_folder_id = self.assets_folder_id
        if subfolder_name:
            target_folder_id = self._ensure_folder(subfolder_name, parent_id=self.assets_folder_id)

        # Check if asset already exists in target folder
        filename = local_path.name
        query = f"'{target_folder_id}' in parents and name = '{filename}' and trashed = false"
        res = self.service.files().list(q=query, fields="files(id, name, size)").execute()
        files = res.get("files", [])

        # Determine mimetype
        suffix = local_path.suffix.lower()
        mime_map = {
            ".mp4": "video/mp4",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ttf": "font/ttf",
        }
        mimetype = mime_map.get(suffix, "application/octet-stream")

        media = MediaFileUpload(str(local_path), mimetype=mimetype, resumable=True)

        if files:
            file_id = files[0]["id"]
            logger.info(f"Updating existing Drive static asset: {filename} in {subfolder_name or 'Assets'} (ID: {file_id})")
            req = self.service.files().update(fileId=file_id, media_body=media, fields="id, name, webViewLink")
        else:
            logger.info(f"Uploading new Drive static asset: {filename} into {subfolder_name or 'Assets'}")
            body = {"name": filename, "parents": [target_folder_id]}
            req = self.service.files().create(body=body, media_body=media, fields="id, name, webViewLink")

        response = None
        while response is None:
            status, response = req.next_chunk()
            if status:
                logger.info(f"Asset upload progress ({filename}): {int(status.progress() * 100)}%")

        uploaded_id = response.get("id")
        logger.info(f"Static asset uploaded successfully: {filename} (ID: {uploaded_id})")
        return {
            "id": uploaded_id,
            "name": filename,
            "link": response.get("webViewLink"),
            "subfolder": subfolder_name,
        }

    def sync_static_assets_from_drive(self, local_assets_dir: Path = Path("assets")) -> List[Path]:
        """Scans Google Drive Assets directory and downloads all static assets to local_assets_dir."""
        if not self.service or not self.assets_folder_id:
            self.connect()

        logger.info(f"Syncing static assets from Google Drive Assets to {local_assets_dir}")
        local_assets_dir.mkdir(parents=True, exist_ok=True)
        synced_files = []

        # 1. List all subfolders and direct files in Assets
        query = f"'{self.assets_folder_id}' in parents and trashed = false"
        res = self.service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = res.get("files", [])

        for item in items:
            item_id = item["id"]
            item_name = item["name"]
            item_mime = item.get("mimeType", "")

            if item_mime == "application/vnd.google-apps.folder":
                # Subfolder (e.g. animations, backgrounds)
                sub_query = f"'{item_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
                sub_res = self.service.files().list(q=sub_query, fields="files(id, name, size)").execute()
                for sub_item in sub_res.get("files", []):
                    target_local = local_assets_dir / item_name / sub_item["name"]
                    if not target_local.exists() or target_local.stat().st_size == 0:
                        logger.info(f"Missing local asset detected: {target_local}. Downloading from Drive...")
                        self.download_file_by_id(sub_item["id"], target_local)
                        synced_files.append(target_local)
                    else:
                        logger.info(f"Static asset {target_local} is already present locally.")
            else:
                # Direct file in Assets
                target_local = local_assets_dir / item_name
                if not target_local.exists() or target_local.stat().st_size == 0:
                    logger.info(f"Missing local asset detected: {target_local}. Downloading from Drive...")
                    self.download_file_by_id(item_id, target_local)
                    synced_files.append(target_local)
                else:
                    logger.info(f"Static asset {target_local} is already present locally.")

        logger.info(f"Static assets sync complete. Downloaded {len(synced_files)} missing asset(s).")
        return synced_files

    def sync_static_assets_to_drive(self, local_assets_dir: Path = Path("assets")) -> List[Dict[str, Any]]:
        """Scans local assets directory and uploads all static assets into Google Drive Assets."""
        if not self.service or not self.assets_folder_id:
            self.connect()

        logger.info(f"Uploading local static assets from {local_assets_dir} to Google Drive Assets")
        uploaded_results = []

        if not local_assets_dir.exists():
            return uploaded_results

        for file_path in local_assets_dir.rglob("*"):
            if file_path.is_file():
                # Check relative subfolder
                rel_path = file_path.relative_to(local_assets_dir)
                subfolder = rel_path.parent.as_posix() if rel_path.parent != Path(".") else None
                res = self.upload_static_asset(local_path=file_path, subfolder_name=subfolder)
                uploaded_results.append(res)

        return uploaded_results
