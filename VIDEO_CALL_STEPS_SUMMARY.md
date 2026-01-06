# 📋 TỔNG HỢP CÁC BƯỚC THỰC HIỆN VIDEO CALL

## 🎯 Tổng quan: 6 PHASE chính, ~20 bước chi tiết

---

## ✅ PHASE 1: BACKEND - WebSocket Schemas & Models (3 bước)

### Bước 1.1: Thêm Call Message Types
**File:** `backend/app/schemas/websocket.py`
- Thêm các enum types: `CALL_INVITE`, `CALL_INVITE_SENT`, `CALL_INCOMING`, `CALL_ACCEPT`, `CALL_ACCEPTED`, `CALL_ACCEPT_OK`, `CALL_REJECT`, `CALL_END`, `CALL_ENDED`, `SDP_OFFER`, `SDP_ANSWER`, `ICE_CANDIDATE`

### Bước 1.2: Tạo Pydantic Models
**File:** `backend/app/schemas/websocket.py`
- Tạo các models: `WSCallInvite`, `WSCallInviteSent`, `WSCallIncoming`, `WSCallAccept`, `WSCallAccepted`, `WSCallReject`, `WSCallEnd`, `WSCallEnded`, `WSSDPOffer`, `WSSDPAnswer`, `WSICECandidate`

### Bước 1.3: Export Models
**File:** `backend/app/schemas/__init__.py`
- Export các models mới

---

## ✅ PHASE 2: BACKEND - Call Session Management (2 bước)

### Bước 2.1: Tạo CallSession Model
**File:** `backend/app/websocket/manager.py`
- Tạo dataclass `CallSession` với fields: `call_id`, `caller_id`, `callee_id`, `state`, `created_at`, `ended_at`

### Bước 2.2: Thêm active_calls Dict
**File:** `backend/app/websocket/manager.py`
- Thêm `self.active_calls: Dict[str, CallSession] = {}` vào `ConnectionManager.__init__()`

---

## ✅ PHASE 3: BACKEND - WebSocket Handlers (1 bước lớn)

### Bước 3.1: Xử lý Call Messages trong WebSocket Endpoint
**File:** `backend/app/api/endpoints/websocket.py`
- Xử lý `call_invite`: Tạo call session, gửi notifications
- Xử lý `call_accept`: Update state, gửi confirmations
- Xử lý `call_reject`: Forward rejection, cleanup
- Xử lý `call_end`: Cleanup và notify peer
- Xử lý `sdp_offer`: Forward SDP offer
- Xử lý `sdp_answer`: Forward SDP answer
- Xử lý `ice_candidate`: Forward ICE candidate

---

## ✅ PHASE 4: FRONTEND - Dependencies (1 bước)

### Bước 4.1: Cài đặt Dependencies
**File:** `frontend/requirements.txt`
- Thêm: `aiortc==1.6.0`, `opencv-python==4.8.1.78`
- Chạy: `pip install -r requirements.txt`

---

## ✅ PHASE 5: FRONTEND - WebSocket Client (2 bước)

### Bước 5.1: Thêm Call Callbacks
**File:** `frontend/app/websocket/client.py`
- Thêm `self.call_callbacks` list
- Thêm methods: `add_call_callback()`, `remove_call_callback()`
- Cập nhật `_listen()` để route call messages đến call_callbacks

### Bước 5.2: Thêm Call Send Methods
**File:** `frontend/app/websocket/client.py`
- Thêm: `send_call_invite()`, `send_call_accept()`, `send_call_reject()`, `send_call_end()`
- Thêm: `send_sdp_offer()`, `send_sdp_answer()`, `send_ice_candidate()`

---

## ✅ PHASE 6: FRONTEND - Video Tracks Utility (1 bước)

### Bước 6.1: Tạo Custom Video Tracks
**File mới:** `frontend/app/utils/video_tracks.py`
- Tạo class `OpenCVVideoTrack` (local video từ camera)
- Tạo class `RemoteVideoTrackProcessor` (remote video processing)

---

## ✅ PHASE 7: FRONTEND - WebRTC Handler (4 bước)

### Bước 7.1: Tạo WebRTCHandler Class (skeleton)
**File mới:** `frontend/app/utils/webrtc_handler.py`
- Tạo class với `__init__()`, `initialize()`, `close()`

### Bước 7.2: Setup Local Video Track
**File:** `frontend/app/utils/webrtc_handler.py`
- Implement `_setup_local_video()` sử dụng `OpenCVVideoTrack`

### Bước 7.3: Setup Local Audio Track
**File:** `frontend/app/utils/webrtc_handler.py`
- Implement `_setup_local_audio()` sử dụng DirectShow (Windows)

### Bước 7.4: WebRTC Signaling Methods
**File:** `frontend/app/utils/webrtc_handler.py`
- Implement `create_offer()`, `create_answer()`, `handle_remote_description()`
- Implement `add_ice_candidate()`, ICE candidate handler
- **⚠️ BẮT BUỘC:** Setup `@pc.on('icecandidate')` event handler để tự động gửi ICE candidates qua WebSocket khi có candidate mới (cần thiết cho NAT traversal)
- Implement remote video track handling với callback

---

## ✅ PHASE 8: FRONTEND - Video Call Page (5 bước)

### Bước 8.1: Tạo VideoCallPage Class (skeleton)
**File mới:** `frontend/app/pages/video_call_page.py`
- Tạo class với UI layout (local/remote video, controls)

### Bước 8.2: Setup Camera Preview
**File:** `frontend/app/pages/video_call_page.py`
- Implement `_setup_camera_preview()` với OpenCV và ft.Timer

### Bước 8.3: WebRTC Initialization
**File:** `frontend/app/pages/video_call_page.py`
- Implement `_initialize_call()` với WebRTCHandler setup
- Setup remote video callback

### Bước 8.4: Signaling Handlers
**File:** `frontend/app/pages/video_call_page.py`
- Implement `handle_sdp_offer()`, `handle_sdp_answer()`, `handle_ice_candidate()`

### Bước 8.5: Call Controls & Cleanup
**File:** `frontend/app/pages/video_call_page.py`
- Implement `_handle_end_call()`, cleanup methods
- Connection state handling và UI updates

---

## ✅ PHASE 9: FRONTEND - Main Screen Integration (5 bước)

### Bước 9.1: Thêm Video Call Button
**File:** `frontend/app/screens/main_screen.py`
- Thêm video call button vào chat header (chỉ direct chat)

### Bước 9.2: Call State Variables
**File:** `frontend/app/screens/main_screen.py`
- Thêm: `current_call_id`, `current_call_page`, `call_timeout_timer`

### Bước 9.3: Start Video Call Logic
**File:** `frontend/app/screens/main_screen.py`
- Implement `_start_video_call()`, `_show_calling_overlay()`

### Bước 9.4: Call Message Handler
**File:** `frontend/app/screens/main_screen.py`
- Implement `handle_call_message()` để xử lý tất cả call events
- Xử lý: `call_invite_sent`, `call_incoming`, `call_accepted`, `call_reject`, `call_ended`, `sdp_offer/answer`, `ice_candidate`

### Bước 9.5: Incoming Call Dialog & Timeout
**File:** `frontend/app/screens/main_screen.py`
- Implement `_show_incoming_call_dialog()` với Accept/Reject
- **⚠️ QUAN TRỌNG:** Dialog phải có **ringtone/sound** để người dùng biết có cuộc gọi đến
  - Sử dụng `ft.Audio` hoặc `playsound` library
  - Phát âm thanh khi dialog hiển thị, dừng khi accept/reject/timeout
  - Lưu ý: Flet không có notification hệ thống, nên sound là cách duy nhất để alert user
- Implement `_handle_call_timeout()` với ft.Timer (30s)
- Implement `_open_video_call_page()`, `_close_video_call_page()`

---

## ✅ PHASE 10: Testing (3 bước)

### Bước 10.1: Test Signaling Flow
- Test call invite → accept → WebRTC connection
- Test reject, timeout, end call

### Bước 10.2: Test WebRTC Connection
- Test video streaming (local và remote)
- Test audio
- Test ICE candidates

### Bước 10.3: Test Edge Cases
- Test busy state (call khi đang trong call khác)
- Test network issues
- Test cleanup

---

## 📊 TỔNG KẾT

### Số lượng:
- **10 PHASE chính**
- **~27 bước chi tiết** (đã bổ sung ICE candidate event handler và ringtone requirement)

### Breakdown:
- **Backend**: 3 phases (6 bước)
- **Frontend**: 6 phases (18 bước)
- **Testing**: 1 phase (3 bước)

### Ưu tiên thực hiện:
1. ✅ Backend trước (PHASE 1-3)
2. ✅ Frontend dependencies (PHASE 4)
3. ✅ Frontend core (PHASE 5-8)
4. ✅ Integration (PHASE 9)
5. ✅ Testing (PHASE 10)

---

## 📝 CHECKLIST TỔNG QUAN

### Backend
- [ ] Phase 1: WebSocket Schemas (3 bước)
- [ ] Phase 2: Call Session Management (2 bước)
- [ ] Phase 3: WebSocket Handlers (1 bước)

### Frontend Core
- [ ] Phase 4: Dependencies (1 bước)
- [ ] Phase 5: WebSocket Client (2 bước)
- [ ] Phase 6: Video Tracks (1 bước)
- [ ] Phase 7: WebRTC Handler (4 bước)
- [ ] Phase 8: Video Call Page (5 bước)

### Frontend Integration
- [ ] Phase 9: Main Screen Integration (5 bước)

### Testing
- [ ] Phase 10: Testing (3 bước)

---

## 🎯 NEXT STEPS

Bắt đầu từ **PHASE 1 - Backend WebSocket Schemas** và làm tuần tự từng phase.

**Lưu ý:** Mỗi phase nên test kỹ trước khi chuyển sang phase tiếp theo!

