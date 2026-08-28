import os
import socket
from datetime import datetime

from dotenv import load_dotenv
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QComboBox, QSpinBox,
    QSlider, QVBoxLayout, QHBoxLayout, QTextEdit, QTabWidget, QFileDialog,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox
)
from PySide6.QtGui import QPixmap

from core.model_manager import ModelManager
from core.model_load_worker import ModelLoadWorker
from core.batch_worker import BatchImageWorker
from core.cloud_sync import CloudSyncWorker
from camera.camera_worker import CameraWorker, list_available_cameras
from database.db_manager import DBManager
from ui.utils import cvimg_to_qpixmap, scale_pixmap_to_label


MODEL_LABELS = {
    "defect": "Pipe Staple Model",
    "tank_screw": "Underbody Screw Model",
}

# ---- Color palette (light / indigo theme) ----
ACCENT = "#4f46e5"        # indigo
ACCENT_HOVER = "#4338ca"
BG_APP = "#f4f5f9"
BG_SIDEBAR = "#ffffff"
BORDER = "#e2e8f0"
TEXT_MAIN = "#1e293b"
TEXT_MUTED = "#64748b"
GOOD_BG = "#ecfdf5"
GOOD_TEXT = "#059669"
BAD_BG = "#fef2f2"
BAD_TEXT = "#dc2626"


class ImageResultCard(QFrame):
    """Result card for a single image (Batch Images tab)"""

    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"QFrame {{ background:{BG_SIDEBAR}; border:1px solid {BORDER}; border-radius:14px; }}")

        outer = QVBoxLayout(self)

        header = QHBoxLayout()
        name_label = QLabel(file_name)
        name_label.setStyleSheet(f"font-weight:700; color:{TEXT_MAIN};")
        self.status_label = QLabel("Analyzing...")
        self.status_label.setStyleSheet(
            f"background:{BORDER}; color:{TEXT_MUTED}; padding:3px 10px; border-radius:10px; font-weight:700; font-size:11px;"
        )
        header.addWidget(name_label)
        header.addStretch()
        header.addWidget(self.status_label)
        outer.addLayout(header)

        imgs_row = QHBoxLayout()
        self.orig_label = QLabel("ORIGINAL")
        self.orig_label.setAlignment(Qt.AlignCenter)
        self.orig_label.setMinimumSize(260, 200)
        self.orig_label.setStyleSheet("background:#f1f5f9; border-radius:10px; color:#94a3b8;")

        self.result_label = QLabel("AI RESULT")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(260, 200)
        self.result_label.setStyleSheet("background:#f1f5f9; border-radius:10px; color:#94a3b8;")

        imgs_row.addWidget(self.orig_label)
        imgs_row.addWidget(self.result_label)
        outer.addLayout(imgs_row)

    def set_original(self, pixmap):
        self.orig_label.setPixmap(scale_pixmap_to_label(pixmap, self.orig_label))

    def set_result(self, pixmap, status, pixel_count):
        self.result_label.setPixmap(scale_pixmap_to_label(pixmap, self.result_label))
        if status == "MISSING":
            self.status_label.setText(f"🚨 MISSING ({pixel_count} PX)")
            self.status_label.setStyleSheet(
                f"background:{BAD_BG}; color:{BAD_TEXT}; padding:3px 10px; border-radius:10px; font-weight:700; font-size:11px;"
            )
        else:
            self.status_label.setText("✅ GOOD")
            self.status_label.setStyleSheet(
                f"background:{GOOD_BG}; color:{GOOD_TEXT}; padding:3px 10px; border-radius:10px; font-weight:700; font-size:11px;"
            )

    def set_error(self):
        self.status_label.setText("❌ ERROR")
        self.status_label.setStyleSheet(
            f"background:{BAD_BG}; color:{BAD_TEXT}; padding:3px 10px; border-radius:10px; font-weight:700; font-size:11px;"
        )


class MainWindow(QMainWindow):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        self.setWindowTitle("R2U-NET Inspection Pro - Desktop (Offline)")
        self.resize(1400, 860)
        self.setStyleSheet(f"QMainWindow {{ background:{BG_APP}; }}")

        self.model_manager = ModelManager(base_dir)
        self.db = DBManager(os.path.join(base_dir, 'data', 'inspections.db'))

        load_dotenv(os.path.join(base_dir, '.env'))
        self.device_id = os.environ.get("DEVICE_ID", socket.gethostname())
        self.cloud_sync = None

        self.camera_worker = None
        self.batch_worker = None
        self.current_source = None  # int camera index, or path string
        self.pending_batch_cards = {}

        self._build_ui()
        self._start_loading_models()
        self._start_cloud_sync()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        root = QHBoxLayout(central)
        self.setCentralWidget(central)

        root.addWidget(self._build_sidebar(), 0)
        root.addWidget(self._build_main_area(), 1)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet(f"QFrame {{ background:{BG_SIDEBAR}; border-right:1px solid {BORDER}; }}")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("⚙️ Control Panel")
        title.setStyleSheet(f"color:{ACCENT}; font-size:20px; font-weight:800;")
        subtitle = QLabel("R2U-NET Segmentation System (Offline)")
        subtitle.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.model_status_label = QLabel("⏳ Loading models...")
        self.model_status_label.setStyleSheet("color:#d97706; font-size:11px; font-weight:700;")
        layout.addWidget(self.model_status_label)

        self.cloud_status_label = QLabel("☁️ Cloud sync: checking...")
        self.cloud_status_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; font-weight:700;")
        layout.addWidget(self.cloud_status_label)

        layout.addWidget(self._label("SELECT AI MODEL"))
        self.model_select = QComboBox()
        for key, label in MODEL_LABELS.items():
            self.model_select.addItem(label, userData=key)
        self._style_input(self.model_select)
        layout.addWidget(self.model_select)

        layout.addWidget(self._label("PIXEL THRESHOLD"))
        self.px_threshold_input = QSpinBox()
        self.px_threshold_input.setRange(1, 200000)
        self.px_threshold_input.setValue(500)
        self._style_input(self.px_threshold_input)
        layout.addWidget(self.px_threshold_input)

        conf_row = QHBoxLayout()
        conf_row.addWidget(self._label("CONFIDENCE"))
        self.conf_value_label = QLabel("0.35")
        self.conf_value_label.setStyleSheet(f"color:{ACCENT}; font-weight:700;")
        conf_row.addStretch()
        conf_row.addWidget(self.conf_value_label)
        layout.addLayout(conf_row)

        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setMinimum(10)
        self.conf_slider.setMaximum(95)
        self.conf_slider.setValue(35)
        self.conf_slider.valueChanged.connect(
            lambda v: self.conf_value_label.setText(f"{v / 100:.2f}")
        )
        layout.addWidget(self.conf_slider)

        layout.addWidget(self._divider())

        layout.addWidget(self._label("CAMERA SOURCE"))
        self.camera_select = QComboBox()
        self._style_input(self.camera_select)
        layout.addWidget(self.camera_select)

        refresh_btn = QPushButton("🔄 Scan Cameras")
        refresh_btn.setStyleSheet(self._secondary_btn_style())
        refresh_btn.clicked.connect(self._refresh_cameras)
        layout.addWidget(refresh_btn)
        self._refresh_cameras()

        layout.addWidget(self._divider())

        self.log_count_label = QLabel(f"Logs Captured: {self.db.count_all()} Items")
        self.log_count_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px;")
        layout.addWidget(self.log_count_label)

        layout.addWidget(self._label("SYSTEM TERMINAL"))
        self.system_log = QTextEdit()
        self.system_log.setReadOnly(True)
        self.system_log.setFixedHeight(160)
        self.system_log.setStyleSheet(
            "background:#0f172a; color:#4ade80; font-family:monospace; font-size:11px; border-radius:10px; padding:6px;"
        )
        layout.addWidget(self.system_log)

        layout.addStretch()
        return sidebar

    def _build_main_area(self):
        wrapper = QWidget()
        v = QVBoxLayout(wrapper)
        v.setContentsMargins(24, 24, 24, 24)

        header = QLabel("R2U-NET PRO — Deep Learning Defect Detection Platform")
        header.setStyleSheet(f"font-size:22px; font-weight:900; color:{TEXT_MAIN};")
        v.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:1px solid {BORDER}; border-radius:12px; background:{BG_SIDEBAR}; }}
            QTabBar::tab {{ background:{BG_APP}; color:{TEXT_MUTED}; padding:10px 20px; margin-right:4px;
                             border-top-left-radius:10px; border-top-right-radius:10px; font-weight:700; }}
            QTabBar::tab:selected {{ background:{BG_SIDEBAR}; color:{ACCENT}; border:1px solid {BORDER}; border-bottom:none; }}
        """)
        self.tabs.addTab(self._build_live_tab(), "🎥 Camera / Video")
        self.tabs.addTab(self._build_batch_tab(), "📷 Batch Images")
        self.tabs.addTab(self._build_history_tab(), "🗂 Inspection History")
        v.addWidget(self.tabs)

        return wrapper

    def _build_live_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)

        controls = QHBoxLayout()
        load_video_btn = QPushButton("📂 Open Video File")
        load_video_btn.setStyleSheet(self._secondary_btn_style())
        load_video_btn.clicked.connect(self._load_video_file)

        self.cam_btn = QPushButton("📹 Open Camera")
        self.cam_btn.setStyleSheet(self._secondary_btn_style())
        self.cam_btn.clicked.connect(self._toggle_camera)

        self.run_ai_btn = QPushButton("▶️ Run AI Analysis")
        self.run_ai_btn.setEnabled(False)
        self.run_ai_btn.setStyleSheet(self._primary_btn_style())
        self.run_ai_btn.clicked.connect(self._toggle_ai)

        controls.addWidget(load_video_btn)
        controls.addWidget(self.cam_btn)
        controls.addWidget(self.run_ai_btn)
        v.addLayout(controls)

        self.status_banner = QLabel("Waiting for Media Input...")
        self.status_banner.setAlignment(Qt.AlignCenter)
        self.status_banner.setFixedHeight(60)
        self.status_banner.setStyleSheet(
            "background:#f1f5f9; color:#94a3b8; font-weight:900; font-size:18px; border-radius:16px;"
        )
        v.addWidget(self.status_banner)

        frames_row = QHBoxLayout()
        self.source_label = QLabel("SOURCE FEED")
        self.source_label.setAlignment(Qt.AlignCenter)
        self.source_label.setMinimumSize(560, 380)
        self.source_label.setStyleSheet("background:#0f172a; border-radius:16px; color:#64748b;")

        self.result_label = QLabel("AI PREDICTION")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setMinimumSize(560, 380)
        self.result_label.setStyleSheet("background:#0f172a; border-radius:16px; color:#64748b;")

        frames_row.addWidget(self.source_label)
        frames_row.addWidget(self.result_label)
        v.addLayout(frames_row)

        return tab

    def _build_batch_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)

        upload_btn = QPushButton("📤 Click to Upload Batch Images (multiple files allowed)")
        upload_btn.setFixedHeight(70)
        upload_btn.setStyleSheet(
            f"QPushButton {{ border:3px dashed {BORDER}; border-radius:20px; font-weight:800; font-size:15px; color:{TEXT_MUTED}; background:{BG_SIDEBAR}; }}"
            f"QPushButton:hover {{ border-color:{ACCENT}; color:{ACCENT}; }}"
        )
        upload_btn.clicked.connect(self._select_images)
        v.addWidget(upload_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        self.batch_results_container = QWidget()
        self.batch_results_container.setStyleSheet("background:transparent;")
        self.batch_results_layout = QVBoxLayout(self.batch_results_container)
        self.batch_results_layout.addStretch()
        scroll.setWidget(self.batch_results_container)
        v.addWidget(scroll)

        return tab

    def _build_history_tab(self):
        tab = QWidget()
        v = QVBoxLayout(tab)

        refresh_btn = QPushButton("🔄 Refresh History")
        refresh_btn.setStyleSheet(self._secondary_btn_style())
        refresh_btn.clicked.connect(self._refresh_history)
        v.addWidget(refresh_btn)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(
            ["Timestamp", "Source", "Model", "Status", "Pixel Count"]
        )
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(self.history_table)

        self._refresh_history()
        return tab

    # ------------------------------------------------------------------
    # small style helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:10px; font-weight:800; letter-spacing:1px;")
        return lbl

    @staticmethod
    def _divider():
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"color:{BORDER};")
        return line

    @staticmethod
    def _style_input(widget):
        widget.setStyleSheet(
            f"background:{BG_APP}; color:{TEXT_MAIN}; padding:8px; border-radius:10px; border:1px solid {BORDER}; font-weight:700;"
        )

    @staticmethod
    def _primary_btn_style():
        return (
            f"QPushButton {{ background:{ACCENT}; color:white; font-weight:700; padding:10px; border-radius:10px; }}"
            f"QPushButton:hover {{ background:{ACCENT_HOVER}; }}"
            f"QPushButton:disabled {{ background:#c7d2fe; color:#eef2ff; }}"
        )

    @staticmethod
    def _secondary_btn_style():
        return (
            f"QPushButton {{ background:{BG_APP}; color:{TEXT_MAIN}; font-weight:700; padding:10px; border-radius:10px; border:1px solid {BORDER}; }}"
            f"QPushButton:hover {{ background:{BORDER}; }}"
        )

    def _log(self, msg):
        self.system_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    # ------------------------------------------------------------------
    # model loading
    # ------------------------------------------------------------------
    def _start_loading_models(self):
        self._log("⏳ Loading AI models from the models/ folder...")
        self.model_load_worker = ModelLoadWorker(self.model_manager)
        self.model_load_worker.progress.connect(self._log)
        self.model_load_worker.finished_ok.connect(self._on_models_loaded)
        self.model_load_worker.failed.connect(self._on_models_failed)
        self.model_load_worker.start()

    def _on_models_loaded(self):
        self.model_status_label.setText("✅ Models ready")
        self.model_status_label.setStyleSheet(f"color:{GOOD_TEXT}; font-size:11px; font-weight:700;")
        self._log("✅ Both models loaded successfully")

    def _on_models_failed(self, msg):
        self.model_status_label.setText("❌ Failed to load models")
        self.model_status_label.setStyleSheet(f"color:{BAD_TEXT}; font-size:11px; font-weight:700;")
        self._log(f"❌ Model loading failed: {msg}")
        QMessageBox.critical(
            self, "Failed to Load Models",
            f"{msg}\n\n"
            f"Make sure defect_model.h5 and r2unet__model_underbody_screw.h5\n"
            f"are placed inside the 'models/' folder."
        )

    # ------------------------------------------------------------------
    # camera controls
    # ------------------------------------------------------------------
    def _refresh_cameras(self):
        self.camera_select.clear()
        cams = list_available_cameras()
        if not cams:
            self.camera_select.addItem("No camera found", userData=None)
        else:
            for idx in cams:
                self.camera_select.addItem(f"Camera #{idx}", userData=idx)

    def _toggle_camera(self):
        if self.camera_worker and self.camera_worker.isRunning() and self.current_source is not None and isinstance(self.current_source, int):
            self._stop_stream()
            self.cam_btn.setText("📹 Open Camera")
            self.cam_btn.setStyleSheet(self._secondary_btn_style())
            return

        cam_idx = self.camera_select.currentData()
        if cam_idx is None:
            QMessageBox.warning(self, "No Camera Found", "No camera is connected to this machine.")
            return

        self._stop_stream()
        self.current_source = cam_idx
        self._start_stream(cam_idx)
        self.cam_btn.setText("🚫 Close Camera")
        self.cam_btn.setStyleSheet(
            "QPushButton { background:#ef4444; color:white; font-weight:700; padding:10px; border-radius:10px; }"
        )
        self._log(f"📸 Camera #{cam_idx} opened")

    def _load_video_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Video Files (*.mp4 *.avi *.mov *.mkv)")
        if not path:
            return
        self._stop_stream()
        self.current_source = path
        self._start_stream(path)
        self._log(f"✅ Video loaded: {os.path.basename(path)}")

    def _start_stream(self, source):
        self.camera_worker = CameraWorker(source, self.model_manager)
        self.camera_worker.frame_ready.connect(self._on_frame_ready)
        self.camera_worker.error.connect(self._log)
        self.camera_worker.start()

        self.run_ai_btn.setEnabled(True)
        self.run_ai_btn.setStyleSheet(self._primary_btn_style())
        self.status_banner.setText("Media Ready - Press Run AI")
        self.status_banner.setStyleSheet(
            "background:#eef2ff; color:#4f46e5; font-weight:900; font-size:18px; border-radius:16px;"
        )

    def _stop_stream(self):
        if self.camera_worker:
            self.camera_worker.ai_enabled = False
            self.camera_worker.stop()
            self.camera_worker = None
        self.run_ai_btn.setEnabled(False)
        self.run_ai_btn.setText("▶️ Run AI Analysis")
        self.run_ai_btn.setStyleSheet(self._primary_btn_style())

    def _toggle_ai(self):
        if not self.camera_worker:
            return
        self.camera_worker.ai_enabled = not self.camera_worker.ai_enabled
        if self.camera_worker.ai_enabled:
            self.camera_worker.model_type = self.model_select.currentData()
            self.camera_worker.conf_threshold = self.conf_slider.value() / 100
            self.camera_worker.px_threshold = self.px_threshold_input.value()
            self.run_ai_btn.setText("⏸️ Stop AI Analysis")
            self.run_ai_btn.setStyleSheet(
                "QPushButton { background:#f43f5e; color:white; font-weight:700; padding:10px; border-radius:10px; }"
            )
            self._log(f"🚀 Analysis started ({self.model_select.currentText()})")
        else:
            self.run_ai_btn.setText("▶️ Run AI Analysis")
            self.run_ai_btn.setStyleSheet(self._primary_btn_style())
            self._log("⏸️ Analysis paused")

    def _on_frame_ready(self, raw_bgr, result_bgr, status, pixel_count):
        self.source_label.setPixmap(scale_pixmap_to_label(cvimg_to_qpixmap(raw_bgr), self.source_label))

        if result_bgr is not None:
            self.result_label.setPixmap(scale_pixmap_to_label(cvimg_to_qpixmap(result_bgr), self.result_label))
            self._update_status_banner(status, pixel_count)
            if status == "MISSING":
                source_name = "Video/Live" if isinstance(self.current_source, str) else "Live Camera"
                self.db.insert_record(
                    source_name, self.model_select.currentData(), status, pixel_count,
                    self.conf_slider.value() / 100, self.px_threshold_input.value()
                )
                self.log_count_label.setText(f"Logs Captured: {self.db.count_all()} Items")

    def _update_status_banner(self, status, pixel_count):
        if status == "MISSING":
            self.status_banner.setText(f"🚨 DEFECT DETECTED: {pixel_count} PX")
            self.status_banner.setStyleSheet(
                "background:#e11d48; color:white; font-weight:900; font-size:18px; border-radius:16px;"
            )
        else:
            self.status_banner.setText("✅ SYSTEM NORMAL (GOOD)")
            self.status_banner.setStyleSheet(
                "background:#059669; color:white; font-weight:900; font-size:18px; border-radius:16px;"
            )

    # ------------------------------------------------------------------
    # batch image processing
    # ------------------------------------------------------------------
    def _select_images(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Images (multiple files allowed)", "", "Images (*.jpg *.jpeg *.png)"
        )
        if not paths:
            return

        if not self.model_manager.is_loaded():
            QMessageBox.warning(self, "Models Not Ready", "Please wait for the AI models to finish loading.")
            return

        self._log(f"🖼 Processing {len(paths)} image(s) with {self.model_select.currentText()} ...")

        for path in paths:
            card = ImageResultCard(os.path.basename(path))
            pix = QPixmap(path)
            card.set_original(pix)
            self.batch_results_layout.insertWidget(0, card)
            self.pending_batch_cards[path] = card

        model_type = self.model_select.currentData()
        conf = self.conf_slider.value() / 100
        px = self.px_threshold_input.value()

        self.batch_worker = BatchImageWorker(paths, self.model_manager, model_type, conf, px)
        self.batch_worker.result_ready.connect(self._on_batch_result)
        self.batch_worker.error.connect(self._on_batch_error)
        self.batch_worker.finished_batch.connect(lambda: self._log("✅ Batch processing complete"))
        self.batch_worker.start()

    def _on_batch_result(self, path, result_bgr, status, pixel_count):
        card = self.pending_batch_cards.pop(path, None)
        if card:
            card.set_result(cvimg_to_qpixmap(result_bgr), status, pixel_count)

        self.db.insert_record(
            os.path.basename(path), self.model_select.currentData(),
            status, pixel_count, self.conf_slider.value() / 100, self.px_threshold_input.value()
        )
        self.log_count_label.setText(f"Logs Captured: {self.db.count_all()} Items")

    def _on_batch_error(self, path, msg):
        card = self.pending_batch_cards.pop(path, None)
        if card:
            card.set_error()
        self._log(f"❌ Error with file {os.path.basename(path)}: {msg}")

    # ------------------------------------------------------------------
    # history
    # ------------------------------------------------------------------
    def _refresh_history(self):
        rows = self.db.fetch_history()
        self.history_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.history_table.setItem(r, c, QTableWidgetItem(str(val)))

    # ------------------------------------------------------------------
    # cloud sync
    # ------------------------------------------------------------------
    def _start_cloud_sync(self):
        self.cloud_sync = CloudSyncWorker(self.db, self.device_id)
        if not self.cloud_sync.is_configured():
            self.cloud_status_label.setText("☁️ Cloud sync: off (no .env configured)")
            self.cloud_status_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; font-weight:700;")
            return

        self.cloud_status_label.setText("☁️ Cloud sync: starting...")
        self.cloud_sync.status_changed.connect(self._on_cloud_status)
        self.cloud_sync.synced_batch.connect(lambda n: self._log(f"☁️ Synced {n} record(s) to the cloud"))
        self.cloud_sync.start()

    def _on_cloud_status(self, msg):
        self._log(msg)
        if "disabled" in msg or "off" in msg:
            self.cloud_status_label.setText("☁️ Cloud sync: off")
            self.cloud_status_label.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; font-weight:700;")
        elif "error" in msg.lower() or "failed" in msg.lower():
            self.cloud_status_label.setText("☁️ Cloud sync: retrying...")
            self.cloud_status_label.setStyleSheet("color:#d97706; font-size:11px; font-weight:700;")
        else:
            self.cloud_status_label.setText("☁️ Cloud sync: active")
            self.cloud_status_label.setStyleSheet(f"color:{GOOD_TEXT}; font-size:11px; font-weight:700;")

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self._stop_stream()
        if self.batch_worker:
            self.batch_worker.stop()
        if self.cloud_sync:
            self.cloud_sync.stop()
        event.accept()
