# Google TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Google Cloud Text-to-Speech for selected custom-word audio regeneration using local ADC auth.

**Architecture:** A small Google TTS helper module handles config, pinyin-to-phoneme SSML, token lookup, and REST synthesis. The custom sync script uses that helper only when explicitly asked to regenerate audio for selected entries.

**Tech Stack:** Python, urllib, subprocess, AnkiConnect, Google Cloud Text-to-Speech REST API

---

### Task 1: Capture the new behavior in tests

**Files:**
- Modify: `tests/test_sync_custom_chinese_support.py`
- Create: `tests/test_google_tts.py`
- Test: `tests/test_sync_custom_chinese_support.py`, `tests/test_google_tts.py`

- [ ] **Step 1: Write failing tests for pinyin-to-phoneme conversion and SSML generation**
- [ ] **Step 2: Run targeted tests and watch them fail**
- [ ] **Step 3: Write failing tests for selected-word regeneration gating**
- [ ] **Step 4: Run targeted tests and watch them fail**

### Task 2: Implement the Google TTS helper

**Files:**
- Create: `scripts/google_tts.py`
- Test: `tests/test_google_tts.py`

- [ ] **Step 1: Add config validation and ADC token lookup**
- [ ] **Step 2: Add marked-pinyin to numbered-pinyin conversion**
- [ ] **Step 3: Add SSML request builder and REST synthesize call**
- [ ] **Step 4: Run targeted tests and make them pass**

### Task 3: Wire selected regeneration into custom sync

**Files:**
- Modify: `scripts/sync_custom_to_chinese_support.py`
- Test: `tests/test_sync_custom_chinese_support.py`

- [ ] **Step 1: Add explicit regeneration flags and entry targeting**
- [ ] **Step 2: Call Google TTS only when regeneration is requested for a selected entry**
- [ ] **Step 3: Keep existing-audio behavior unchanged otherwise**
- [ ] **Step 4: Run targeted tests and make them pass**

### Task 4: Document the workflow

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document Google auth setup and env vars**
- [ ] **Step 2: Document selected-word regeneration commands**

### Task 5: Verify end to end

**Files:**
- Modify: none
- Test: `tests/test_google_tts.py`, `tests/test_sync_custom_chinese_support.py`, full test suite

- [ ] **Step 1: Run targeted Python tests**
- [ ] **Step 2: Run the full Python suite**
- [ ] **Step 3: If credentials and network allow, run one small live synthesis smoke test**
