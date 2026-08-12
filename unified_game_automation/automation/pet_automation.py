import os
import re
import time
import numpy as np
from PIL import Image

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    ort = None

from core.base_automation import BaseAutomation


class PetAutomation(BaseAutomation):
    """
    PetAutomation Class - Refactored with YOLO26 (ONNX) Object Detection & OCR Integration.
    Supports 3 Detection Modes:
    - 'ocr': OCR Only
    - 'yolo': YOLO26 Only
    - 'hybrid': OCR + YOLO26 (Hybrid Mode)
    """

    def __init__(self, game_connector, ocr_engine=None, status_callback=None, bot_core=None, on_target_found=None):
        if status_callback is not None and hasattr(status_callback, 'stop_event'):
            if bot_core is not None and on_target_found is None:
                on_target_found = bot_core
            bot_core = status_callback
            status_callback = None

        super().__init__(
            game_connector=game_connector,
            ocr_engine=ocr_engine,
            bot_core=bot_core,
            name="Pet",
        )
        self.status_callback = status_callback
        self.on_target_found = on_target_found
        
        # Detection ROI Areas
        self.area = None          # Legacy / default area
        self.ocr_area = None      # ROI specifically for OCR
        self.yolo_area = None     # ROI specifically for YOLO26 Bounding Box Detection

        # Targets & Options
        self.targets = []         # OCR target text phrases
        self.yolo_targets = []    # YOLO target class names or class IDs (OR logic matching)
        self.yolo_class_names = []# Class names mapping list or dict for YOLO model
        
        # YOLO ONNX Model Configurations
        self.yolo_model_path = ""
        self.yolo_session = None
        self.yolo_conf_threshold = 0.25
        self.yolo_iou_threshold = 0.45
        self.detection_mode = "ocr"  # Modes: 'ocr', 'yolo', 'hybrid'

        # Step coordinates for click sequence
        self.coords = {
            "pet_training": None,
            "untrain_icon": None,
            "wrong_slot": None,
            "untrain_btn": None,
            "yes_btn": None,
        }

        # Stat tracking & debouncing
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        self._thread_name = "pet-automation-loop"
        self._last_yolo_hit_at = 0.0
        self._yolo_debounce_sec = 0.4

    # -------------------------------------------------------------------------
    # 1. การกำหนดพื้นที่ตรวจจับ (ROI Area Selection)
    # -------------------------------------------------------------------------

    def set_area(self, area):
        """กำหนดพื้นที่เป้าหมายหลัก (Legacy) และตั้งค่า ocr_area เป็นค่าเริ่มต้น"""
        self.area = area
        self.ocr_area = area

    def set_ocr_area(self, area):
        """กำหนดขอบเขตพื้นที่ ROI สำหรับการตรวจจับข้อความด้วย OCR โดยเฉพาะ"""
        self.ocr_area = area
        self.area = area

    def set_yolo_area(self, area):
        """
        กำหนดขอบเขตพื้นที่ ROI สำหรับการตรวจจับวัตถุด้วย YOLO26 โดยเฉพาะ
        ช่วยป้องกันการตรวจจับสิ่งของนอกพื้นที่เป้าหมาย (Bounding Box Crop)
        """
        self.yolo_area = area

    def get_yolo_area(self):
        """
        ดึงพื้นที่ ROI ของ YOLO หากผู้ใช้ไม่ได้ตั้งค่าไว้
        จะทำการ Fallback ไปใช้ ocr_area หรือพื้นที่หลัก (area) โดยอัตโนมัติ
        """
        if self.yolo_area:
            return self.yolo_area
        return self.ocr_area or self.area

    # -------------------------------------------------------------------------
    # 2. โครงสร้างการโหลดโมเดล ONNX (YOLO26) และตั้งค่า
    # -------------------------------------------------------------------------

    def set_yolo_model_path(self, model_path):
        """
        กำหนด Path ของไฟล์โมเดล ONNX (.onnx) สำหรับ YOLO26
        เมื่อมีการเปลี่ยน Path จะรีเซ็ต Session เพื่อเตรียมโหลดใหม่
        """
        if self.yolo_model_path != model_path:
            self.yolo_model_path = model_path
            self.yolo_session = None

    def set_yolo_class_names(self, class_names):
        """กำหนดรายการชื่อคลาส (Class Names) ของโมเดล YOLO26"""
        self.yolo_class_names = class_names

    def set_yolo_conf_threshold(self, threshold):
        """กำหนดค่า Confidence Threshold สำหรับคัดกรองผลการตรวจจับ YOLO"""
        self.yolo_conf_threshold = max(0.01, min(1.0, float(threshold)))

    def _load_yolo_model(self):
        """
        โหลดโมเดล ONNX ด้วย onnxruntime
        รองรับทั้ง GPU (CUDA) และ CPU Execution Providers
        """
        if not ONNX_AVAILABLE:
            return False, "onnxruntime package is not installed"
        if not self.yolo_model_path:
            return False, "YOLO model path is not set"
        if not os.path.exists(self.yolo_model_path):
            return False, f"Model file not found: {self.yolo_model_path}"

        try:
            available_providers = ort.get_available_providers()
            desired_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            providers = [p for p in desired_providers if p in available_providers]
            if not providers:
                providers = ['CPUExecutionProvider']

            self.yolo_session = ort.InferenceSession(self.yolo_model_path, providers=providers)
            
            # อ่านชื่อคลาสที่ฝั่งไว้ใน Metadata ของไฟล์ ONNX อัตโนมัติ (ถ้ามี)
            try:
                meta = self.yolo_session.get_modelmeta().custom_metadata_map
                if "names" in meta:
                    import json
                    raw_str = meta["names"].replace("'", '"')
                    raw_names = json.loads(raw_str)
                    if isinstance(raw_names, dict):
                        sorted_keys = sorted([int(k) for k in raw_names.keys()])
                        self.yolo_class_names = [str(raw_names[str(k)]) for k in sorted_keys]
                    elif isinstance(raw_names, list):
                        self.yolo_class_names = [str(v) for v in raw_names]
            except Exception:
                pass

            return True, ""
        except Exception as e:
            self.yolo_session = None
            return False, f"Failed to load ONNX session: {e}"

    # -------------------------------------------------------------------------
    # 3. ระบบเลือกคลาสเป้าหมายด้วย OR Logic & โหมดการตรวจจับ
    # -------------------------------------------------------------------------

    def set_yolo_targets(self, target_classes: list):
        """
        กำหนดรายการคลาสเป้าหมายที่ต้องการตรวจจับ (YOLO Target Classes)
        รองรับรายการเป็นชื่อคลาส (String) หรือ Index ของคลาส (Int)
        """
        self.yolo_targets = target_classes or []

    def set_ocr_search_texts(self, targets):
        """จัดเตรียมและคัดกรองคำค้นหา OCR (คำยาวมาก่อนคำสั้นเพื่อความแม่นยำ)"""
        normalized_targets = []
        for target in (targets or []):
            normalized = self.normalize_text(target)
            if not normalized or normalized in normalized_targets:
                continue
            normalized_targets.append(normalized)
            words = normalized.split()
            if len(words) > 3:
                fallback = " ".join(words[:-1])
                if fallback and fallback not in normalized_targets:
                    normalized_targets.append(fallback)

        self.targets = sorted(normalized_targets, key=lambda s: (-len(s), s))

    def set_ocr_targets(self, targets):
        self.set_ocr_search_texts(targets)

    def set_detection_mode(self, mode):
        """
        ตั้งค่าโหมดการตรวจจับเป้าหมาย:
        - 'ocr' / 'OCR Only': ใช้ OCR ตรวจจับข้อความอย่างเดียว
        - 'yolo' / 'YOLO Only': ใช้ YOLO26 ตรวจจับวัตถุอย่างเดียว
        - 'hybrid' / 'OCR + YOLO': ใช้ทั้ง OCR และ YOLO26 ร่วมกัน
        """
        if not mode:
            self.detection_mode = "ocr"
            return
        m = str(mode).strip().lower()
        if "hybrid" in m or "both" in m or "+" in m:
            self.detection_mode = "hybrid"
        elif "yolo" in m:
            self.detection_mode = "yolo"
        else:
            self.detection_mode = "ocr"

    # -------------------------------------------------------------------------
    # พิกัดสำหรับขั้นตอนการทำงาน (Step Coordinates)
    # -------------------------------------------------------------------------

    def set_step_coords(self, step_name, coords):
        step_map = {
            "Pet training": "pet_training",
            "Click on untrain pet icon": "untrain_icon",
            "Click on wrong slot": "wrong_slot",
            "Click untrain button": "untrain_btn",
            "Click yes button": "yes_btn",
        }
        key = step_map.get(step_name, step_name)
        if key in self.coords:
            self.coords[key] = coords

    def set_pet_training_coords(self, coords):
        self.coords["pet_training"] = coords

    def set_untrain_pet_icon_coords(self, coords):
        self.coords["untrain_icon"] = coords

    def set_wrong_slot_coords(self, coords):
        self.coords["wrong_slot"] = coords

    def set_untrain_button_coords(self, coords):
        self.coords["untrain_btn"] = coords

    def set_yes_button_coords(self, coords):
        self.coords["yes_btn"] = coords

    # -------------------------------------------------------------------------
    # 5. การตรวจสอบความพร้อมก่อนเริ่มทำงาน (_validate_config)
    # -------------------------------------------------------------------------

    def _validate_config(self):
        """
        ตรวจสอบความถูกต้องของ Configuration ตามโหมดที่ใช้งานก่อนเปิดการทำงาน
        """
        if not self.core:
            return False, "BotCore is not available"

        missing = [name for name, value in self.coords.items() if not value]
        if missing:
            return False, f"Missing coordinates: {', '.join(missing)}"

        # ตรวจสอบความพร้อมฝั่ง OCR เมื่อเปิดใช้โหมด OCR หรือ Hybrid
        if self.detection_mode in ["ocr", "hybrid"]:
            if not self.ocr_area and not self.area:
                return False, "OCR area not set"
            if not self.targets:
                return False, "No OCR targets selected"

        # ตรวจสอบความพร้อมฝั่ง YOLO เมื่อเปิดใช้โหมด YOLO หรือ Hybrid
        if self.detection_mode in ["yolo", "hybrid"]:
            if not self.yolo_model_path:
                return False, "YOLO model path not set"
            if not os.path.exists(self.yolo_model_path):
                return False, f"YOLO model file does not exist: {self.yolo_model_path}"
            if not self.get_yolo_area():
                return False, "YOLO area not set (and no fallback OCR area)"
            if not self.yolo_targets:
                return False, "No YOLO target classes selected"
            
            # โหลด ONNX Session หากยังไม่ได้เตรียมไว้
            if self.yolo_session is None:
                ok, err = self._load_yolo_model()
                if not ok:
                    return False, f"YOLO ONNX init failed: {err}"

        return True, ""

    def start(self):
        is_ok, message = self._validate_config()
        if not is_ok:
            self.update_status(message)
            return False
        if self.running:
            self.update_status("Already running")
            return False
        if not super().start():
            return False
        self.update_status(f"Automation started (Mode: {self.detection_mode.upper()})")
        
        self.stat_counter = {}
        self.unmapped_ocr_counter = {}
        
        self.core.start_watchdog(timeout_sec=10.0, check_interval_sec=1.0)
        self.core.register_thread(self._thread_name, self._run_loop, daemon=True)
        return True

    def stop(self):
        was_running = self.running
        self.running = False
        if self.core:
            self.core.stop()
            self.core.end_run(tool_name="Pet Untrain")
        if was_running:
            self.update_status("Automation stopped")

    def emergency_stop(self):
        self.running = False
        if self.core:
            self.core.emergency_stop()
            self.core.end_run(tool_name="Pet Untrain")
        self.update_status("EMERGENCY STOP")

    # -------------------------------------------------------------------------
    # Loop การทำงานหลัก
    # -------------------------------------------------------------------------

    def _run_loop(self):
        steps = [
            ("pet_training", "Pet Training"),
            ("untrain_icon", "Untrain Icon"),
            ("wrong_slot", "Wrong Slot"),
            ("untrain_btn", "Untrain"),
            ("yes_btn", "Yes"),
        ]

        def one_cycle():
            if not self.running or self.stop_event.is_set():
                return False

            # ตรวจสอบการพบเป้าหมายตอนเริ่มต้นรอบ
            if self._check_detection_and_stop():
                return False

            for key, label in steps:
                if not self.running or self.stop_event.is_set():
                    return False
                if self._check_detection_and_stop():
                    return False
                if not self.protected_click(self.coords.get(key)):
                    self.update_status(f"Failed to click {label}")
                    return False
                if not self.safe_sleep_ms(self.delay_ms):
                    return False
                if self._check_detection_and_stop():
                    return False
            return True

        try:
            self.safe_loop("pet-main-loop", one_cycle)
        finally:
            self.running = False

    # -------------------------------------------------------------------------
    # OCR Logic
    # -------------------------------------------------------------------------

    def _ocr_contains_ignore_variants(self, normalized, suffix):
        if not suffix:
            return False
        return any(
            variant in normalized
            for variant in [
                f"ignore {suffix}",
                f"nore {suffix}",
                f"gnore {suffix}",
                f"bnor {suffix}",
                f"nor {suffix}",
            ]
        )

    def _ocr_match_pet_targets(self):
        """
        ระบบจับคู่ข้อความ OCR สำหรับ Pet Untrain
        """
        target_area = self.ocr_area or self.area
        if not self.ocr_engine or not target_area or not self.targets:
            return False, ""
        screenshot = self.game_connector.take_screenshot(target_area)
        if screenshot is None:
            return False, ""

        raw = self.ocr_engine.extract_text(screenshot)
        normalized = self.normalize_text(raw)
        now = time.time()

        if normalized.strip():
            text_key = normalized.strip()[:80]
            self.unmapped_ocr_counter[text_key] = self.unmapped_ocr_counter.get(text_key, 0) + 1

        for target in self.targets:
            target_norm = target
            if not target_norm:
                continue

            if target_norm == "penetration":
                if "ignore penetration" in normalized:
                    continue
                if "penetration" in normalized:
                    if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                        return False, normalized
                    self._last_ocr_hit_at = now
                    return True, normalized
                continue

            if target_norm == "resist critical damage":
                if self._ocr_contains_ignore_variants(normalized, "resist critical damage"):
                    continue

            if target_norm == "ignore resist critical damage":
                if self._ocr_contains_ignore_variants(normalized, "resist critical damage"):
                    if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                        return False, normalized
                    self._last_ocr_hit_at = now
                    return True, normalized
                continue

            if target_norm == "resist critical rate":
                if self._ocr_contains_ignore_variants(normalized, "resist critical rate"):
                    continue

            if target_norm == "ignore resist critical rate":
                if self._ocr_contains_ignore_variants(normalized, "resist critical rate"):
                    if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                        return False, normalized
                    self._last_ocr_hit_at = now
                    return True, normalized
                continue

            if target_norm in normalized:
                if now - self._last_ocr_hit_at < self._ocr_debounce_sec:
                    return False, normalized
                self._last_ocr_hit_at = now
                return True, normalized

        return False, normalized

    # -------------------------------------------------------------------------
    # YOLO26 ONNX Preprocessing, Inference, Postprocessing & OR Logic
    # -------------------------------------------------------------------------

    def _nms(self, boxes, scores, iou_threshold=0.45):
        """
        Non-Maximum Suppression (NMS) สำหรับกรอง Bounding Boxes ที่ทับซ้อนกัน
        """
        if len(boxes) == 0:
            return []
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 2]
        y2 = boxes[:, 3]
        areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            if order.size == 1:
                break
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h

            union = areas[i] + areas[order[1:]] - inter
            iou = np.zeros_like(inter)
            non_zero = union > 0
            iou[non_zero] = inter[non_zero] / union[non_zero]

            inds = np.where(iou <= iou_threshold)[0]
            order = order[inds + 1]
        return keep

    def _yolo_match_targets(self):
        """
        ประมวลผล Object Detection ด้วย YOLO26 ONNX ตามลำดับขั้นตอน:
        1. Preprocessing: Crop ROI (yolo_area), Resize, Normalize, CHW Transpose
        2. ONNX Inference: ส่ง Tensor เข้า InferenceSession
        3. Postprocessing & NMS: กรองด้วย confidence & IoU threshold
        4. OR Logic Matching: หากพบ *คลาสใดคลาสหนึ่ง* ตรงกับ yolo_targets ถือว่าเจอเป้าหมาย
        """
        if not self.yolo_session:
            ok, _ = self._load_yolo_model()
            if not ok:
                return False, "", 0.0, None

        # =====================================================================
        # ขั้นตอนที่ 1: Raw Image Capture & Preprocessing
        # =====================================================================
        # 1.1 ใช้ภาพ Raw Capture โดยตรงจาก Game Connector
        roi_area = self.get_yolo_area()
        screenshot = self.game_connector.take_screenshot(roi_area) if roi_area else self.game_connector.take_screenshot()
        if screenshot is None:
            screenshot = self.game_connector.take_screenshot()

        if screenshot is None:
            return False, "", 0.0, None

        # แปลงเป็น RGB จากรูป Raw ที่ capture ได้โดยตรง
        if isinstance(screenshot, Image.Image):
            img_rgb = screenshot.convert("RGB")
        elif isinstance(screenshot, np.ndarray):
            img_rgb = Image.fromarray(np.uint8(screenshot)).convert("RGB")
        else:
            return False, "", 0.0, None


        # 1.2 อ่านขนาด Input shape ที่โมเดล ONNX ต้องการ (เช่น 1x3x640x640)
        try:
            model_input = self.yolo_session.get_inputs()[0]
            input_shape = model_input.shape  # [batch, channels, height, width]
            target_h = input_shape[2] if isinstance(input_shape[2], int) and input_shape[2] > 0 else 640
            target_w = input_shape[3] if isinstance(input_shape[3], int) and input_shape[3] > 0 else 640
            input_name = model_input.name
        except Exception:
            target_h, target_w = 640, 640
            input_name = self.yolo_session.get_inputs()[0].name

        # 1.3 Resize ภาพไปยังขนาดที่โมเดลต้องการ (e.g. 640x640)
        resized_img = img_rgb.resize((target_w, target_h), Image.Resampling.BILINEAR)

        # 1.4 Normalize พิกเซล [0, 255] เป็น [0.0, 1.0], เปลี่ยนรูปแบบ HWC -> CHW และเพิ่ม Batch dimension
        img_np = np.array(resized_img, dtype=np.float32) / 255.0  # (H, W, C)
        img_np = np.transpose(img_np, (2, 0, 1))                   # (C, H, W)
        input_tensor = np.expand_dims(img_np, axis=0)              # (1, C, H, W)

        # =====================================================================
        # ขั้นตอนที่ 2: ONNX Model Inference
        # =====================================================================
        try:
            outputs = self.yolo_session.run(None, {input_name: input_tensor})
            if not outputs:
                return False, "", 0.0, None
            output = outputs[0]
        except Exception as e:
            self.update_status(f"YOLO Inference error: {e}")
            return False, "", 0.0, None

        # =====================================================================
        # ขั้นตอนที่ 3: Postprocessing (Confidence Filter & NMS)
        # =====================================================================
        if output.ndim == 3:
            output = output[0]  # เอา Batch dimension ออก -> (C, N) หรือ (N, C) หรือ (N, 6)

        boxes = np.empty((0, 4))
        scores = np.empty((0,))
        class_ids = np.empty((0,), dtype=int)

        # Format A: End-to-End ONNX NMS Output (N, 6) -> [x1, y1, x2, y2, score, class_id]
        if output.ndim == 2 and output.shape[1] in [6, 7]:
            offset = 0 if output.shape[1] == 6 else 1
            boxes = output[:, offset:offset+4]
            scores = output[:, offset+4]
            class_ids = output[:, offset+5].astype(int)

        # Format B: Standard Raw YOLO Output (C, N) หรือ (N, C) โดย C = 4 + num_classes
        elif output.ndim == 2:
            if output.shape[0] < output.shape[1] and output.shape[0] >= 5:
                output = output.T  # สลับเป็น (N, C)

            if output.shape[1] >= 5:
                boxes_cxcywh = output[:, :4]
                class_scores = output[:, 4:]

                if class_scores.shape[1] > 0:
                    class_ids = np.argmax(class_scores, axis=1)
                    scores = np.max(class_scores, axis=1)

                    # แปลงพิกัดแบบ Center (cx, cy, w, h) เป็น Corner (x1, y1, x2, y2)
                    cx, cy = boxes_cxcywh[:, 0], boxes_cxcywh[:, 1]
                    w, h = boxes_cxcywh[:, 2], boxes_cxcywh[:, 3]
                    x1 = cx - w / 2.0
                    y1 = cy - h / 2.0
                    x2 = cx + w / 2.0
                    y2 = cy + h / 2.0
                    boxes = np.column_stack([x1, y1, x2, y2])

        # 3.1 กรอง Bounding Boxes ด้วย Confidence Threshold
        conf_mask = scores >= self.yolo_conf_threshold
        boxes = boxes[conf_mask]
        scores = scores[conf_mask]
        class_ids = class_ids[conf_mask]

        if len(boxes) == 0:
            return False, "", 0.0, None

        # 3.2 ใช้ NMS หากเป็นดิบ Output (ไม่ใช่ End-to-End ONNX NMS)
        if output.shape[1] not in [6, 7]:
            keep_indices = self._nms(boxes, scores, iou_threshold=self.yolo_iou_threshold)
            boxes = boxes[keep_indices]
            scores = scores[keep_indices]
            class_ids = class_ids[keep_indices]

        # =====================================================================
        # ขั้นตอนที่ 4: การตรวจสอบคลาสเป้าหมายด้วย OR Logic
        # =====================================================================
        normalized_yolo_targets = [str(t).strip().lower() for t in self.yolo_targets]
        all_detections = []
        matched_result = None

        for i in range(len(boxes)):
            cid = int(class_ids[i])
            conf = float(scores[i])
            box = boxes[i].tolist()

            if isinstance(self.yolo_class_names, (list, tuple)) and 0 <= cid < len(self.yolo_class_names):
                cname = str(self.yolo_class_names[cid])
            elif isinstance(self.yolo_class_names, dict) and cid in self.yolo_class_names:
                cname = str(self.yolo_class_names[cid])
            else:
                cname = str(cid)

            cname_lower = cname.strip().lower()
            cid_str = str(cid)
            is_matched = (cname_lower in normalized_yolo_targets or cid_str in normalized_yolo_targets or cid in self.yolo_targets)

            det_item = {"cname": cname, "cid": cid, "conf": conf, "box": box, "matched": is_matched}
            all_detections.append(det_item)

            if is_matched and matched_result is None:
                matched_result = (True, cname, conf, box, cid)

        if matched_result:
            return matched_result[0], matched_result[1], matched_result[2], matched_result[3], matched_result[4], all_detections

        return False, "", 0.0, None, -1, all_detections

    # -------------------------------------------------------------------------
    # 4. รวมระบบตรวจจับและสั่งหยุด (_check_detection_and_stop)
    # -------------------------------------------------------------------------

    def _check_detection_and_stop(self):
        """
        ฟังก์ชันตรวจจับรวม (Unified Detection Check) เรียกใช้แทน _check_ocr_and_stop() ในทุก Step
        รองรับโหมด OCR, YOLO26 และ Hybrid (OCR + YOLO)
        แสดงผลการตรวจจับทุกรอบลงใน Console Log
        เมื่อพบเป้าหมาย:
        1. อัปเดตและแสดง Status ผลลัพธ์
        2. เรียก Callback self.on_target_found(...)
        3. สั่งหยุดสคริปต์อัตโนมัติด้วย self.stop()
        """
        now = time.time()

        # 1. การตรวจจับด้วย OCR (หากเปิดใช้งานโหมด 'ocr' หรือ 'hybrid')
        if self.detection_mode in ["ocr", "hybrid"]:
            matched_ocr, normalized = self._ocr_match_pet_targets()
            if normalized.strip():
                self.update_status(f"[OCR Scan] Text: \"{normalized[:80]}\"")
            else:
                self.update_status("[OCR Scan] Text: (Empty / Unreadable)")

            if matched_ocr:
                msg = f"OCR Target Matched: {normalized[:80]}"
                self.update_status(msg)
                if self.on_target_found:
                    try:
                        self.on_target_found("ocr", normalized)
                    except TypeError:
                        self.on_target_found(normalized)
                    except Exception as e:
                        self.update_status(f"Callback error: {e}")
                self.stop()
                return True

        # 2. การตรวจจับด้วย YOLO26 (หากเปิดใช้งานโหมด 'yolo' หรือ 'hybrid')
        if self.detection_mode in ["yolo", "hybrid"]:
            yolo_res = self._yolo_match_targets()
            matched_yolo = yolo_res[0]
            all_dets = yolo_res[5] if len(yolo_res) > 5 else []

            # แสดงผลการตรวจจับทุกรอบลงใน Console Log
            if all_dets:
                det_lines = [
                    f"--- Detection Results for: ROI Crop ---",
                    f"[+] Found {len(all_dets)} detection(s):\n"
                ]
                for idx, det in enumerate(all_dets, 1):
                    cname = det["cname"]
                    cid = det["cid"]
                    conf_pct = (det["conf"] * 100.0) if det["conf"] <= 1.0 else det["conf"]
                    x1, y1, x2, y2 = det["box"]
                    w = abs(x2 - x1)
                    h = abs(y2 - y1)
                    target_mark = " ✓ TARGET MET" if det["matched"] else ""
                    det_lines.append(f"  Box #{idx}:")
                    det_lines.append(f"    - Label      : {cname} (ID: {cid}){target_mark}")
                    det_lines.append(f"    - Confidence : {conf_pct:.2f}%")
                    det_lines.append(f"    - BoundingBox: [x1={x1:.2f}, y1={y1:.2f}, x2={x2:.2f}, y2={y2:.2f}]")
                    det_lines.append(f"    - Box Size   : Width={w:.2f}px, Height={h:.2f}px")

                det_msg = "\n".join(det_lines)
                self.update_status(det_msg)
            else:
                self.update_status(f"[YOLO Scan] No objects detected (conf >= {self.yolo_conf_threshold:.2f})")

            if matched_yolo:
                if now - self._last_yolo_hit_at < self._yolo_debounce_sec:
                    return False
                self._last_yolo_hit_at = now

                class_name = yolo_res[1]
                conf = yolo_res[2]
                bbox = yolo_res[3] or [0.0, 0.0, 0.0, 0.0]
                cid = yolo_res[4] if len(yolo_res) > 4 else 0
                conf_pct = conf * 100.0 if conf <= 1.0 else conf

                if self.on_target_found:
                    try:
                        self.on_target_found("yolo", class_name, conf_pct, bbox, cid)
                    except TypeError:
                        try:
                            self.on_target_found("yolo", class_name)
                        except TypeError:
                            self.on_target_found(class_name)
                        except Exception as e:
                            self.update_status(f"Callback error: {e}")
                    except Exception as e:
                        self.update_status(f"Callback error: {e}")

                self.stop()
                return True

        return False

    def _check_ocr_and_stop(self):
        """Alias สำหรับ _check_detection_and_stop เพื่อความคงเดิมของโค้ดเรียกเก่า"""
        return self._check_detection_and_stop()