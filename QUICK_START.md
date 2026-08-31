# QUICK START — STUDENT EXAM PLATFORM

## Start the Server

### Open Terminal
```bash
cd "C:\Users\MPaul\OneDrive - Flexera, Inc\Desktop\Per\Edtech"
```

### Start Flask
```bash
.\.venv\Scripts\python.exe exam_platform\app.py
```

### Expected Output
```
* Running on http://127.0.0.1:5000
* Press CTRL+C to quit
```

---

## Access the Platform

### Open Browser
- **URL:** http://localhost:5000
- **Browser:** Chrome, Firefox, Safari, Edge (any modern browser)

### You Should See
- Test listing page showing "Mock Mathematics Assessment"
- Test details: 120 minutes, 19 marks, 8 questions
- "Start Test" button

---

## Student Test Workflow

### Step 1: Select Test
- Click "Start Test" button

### Step 2: Read Instructions
- Review test instructions
- Click "Start Test" button to begin

### Step 3: Answer MCQ Questions (Q1–Q4)
- **Question 1:** "What is 2 + 2?" → Select B) 4
- **Question 2:** "What is the square root of 16?" → Select C) 4
- **Question 3:** "What is the value of π?" → Select options
- **Question 4:** "Solve: 3x = 12" → Select options

**How to Answer:**
- Click on the option (A, B, C, or D)
- Selection saves automatically
- Use "Next" or question navigator to move between questions

### Step 4: Answer Subjective Questions (Q5–Q8)
- **Question 5:** "Solve the quadratic equation: x² - 5x + 6 = 0"
- **Question 6:** "Find derivative of f(x) = x³ + 2x²"
- **Question 7:** "Prove sum of angles in triangle is 180°"
- **Question 8:** "Solve system of equations"

**How to Answer:**
1. **Select Final Answer:** Choose from A, B, C, or D
2. **Upload Solution:** 
   - Click "Click to upload or drag and drop"
   - Select a JPG/JPEG/PNG file from your computer
   - File size limit: 50MB per image
   - You can upload multiple pages/images per question

### Step 5: Navigate
- **Next/Previous Buttons:** Move one question at a time
- **Question Navigator:** Click any question number on the left to jump directly
- **Blue Highlight:** Shows current question
- **Visual Indicator:** 
  - ✓ Answered questions appear answered
  - — Unanswered questions appear empty

### Step 6: Monitor Time
- **Timer:** Top right corner shows remaining time
- **Format:** HH:MM:SS (e.g., 1:45:30)
- **Warning:** Timer turns yellow at 5 minutes, red at 1 minute
- **Auto-Submit:** Test automatically submits when time expires

### Step 7: Submit Test
- Click "Submit Test" button (green, at the top)
- A popup appears showing:
  - Total questions: 8
  - Answered: X questions
  - Unanswered: Y questions
- Click "Submit Test" button in the popup to confirm
- Click "Cancel" if you want to keep working

### Step 8: Confirm Submission
- After submitting, you see a confirmation page
- Shows: "Test submitted successfully"
- Click "Back to Tests" to return to test listing

---

## Test Navigation Tips

### Question Navigator
- Left sidebar shows all 8 questions
- Current question is highlighted in blue
- Click any number to jump to that question

### Previous/Next Buttons
- "← Previous" goes back one question
- "Next →" advances one question
- Previous is disabled on Question 1

### Answering and Navigation
- Answers are saved automatically
- You can change answers anytime
- Navigate freely between questions
- Your answers are remembered when you come back

---

## Image Upload Tips

### For Subjective Questions
1. Prepare a clear image or photo of your handwritten solution
2. Click the upload area or drag and drop
3. Only JPG, JPEG, or PNG files accepted
4. Maximum 50MB per image
5. Can upload multiple images (for multi-page solutions)

### File Requirements
- Format: JPG, JPEG, or PNG
- Size: Maximum 50MB
- Quality: Clear, legible handwriting
- No video or document files

### Upload Workflow
1. Click upload area
2. Select file from computer
3. Preview appears showing uploaded image
4. Can delete and re-upload if needed
5. Can add additional images for more pages

---

## Running Automated Tests

### Test All API Endpoints
```bash
.\.venv\Scripts\python.exe test_exam_platform.py
```

### Expected Output
```
=== EXAM PLATFORM TEST SUITE ===

[OK] Homepage loads
[OK] Test listing page works
[OK] Test instructions page works
[OK] Test start works (Attempt ID: ATTEA781...)
[OK] Questions loaded (8 questions)
[OK] MCQ response saved
[OK] Subjective response saved
[OK] Submission preview works (Answered: 2/8)
[OK] Test submitted successfully
[OK] Confirmation page works

=== ALL TESTS PASSED ===
```

---

## Troubleshooting

### Server Won't Start
- Check if port 5000 is already in use
- Try: `netstat -ano | findstr :5000`
- Kill process if needed

### Page Won't Load
- Check server is running (you should see output in terminal)
- Clear browser cache (Ctrl+Shift+Delete)
- Try different browser
- Check URL: should be http://localhost:5000

### Answers Not Saving
- Check browser console for errors (F12)
- Ensure JavaScript is enabled
- Try refreshing page (F5)
- Try different browser

### Image Upload Issues
- Check file format (only JPG/JPEG/PNG allowed)
- Check file size (max 50MB)
- Check file path has no special characters
- Try uploading a different file first

### Timer Issues
- Timer is client-side only (for MVP)
- If timer seems wrong, refresh the page
- Timer will auto-submit test when it reaches 0:00:00

### Server Crashes
- Read error message in terminal
- Check for specific error details
- Restart server with fresh start

---

## Mock Test Specifications

### Test Details
- **Name:** Mock Mathematics Assessment
- **Subject:** Mathematics
- **Class:** 10
- **Duration:** 120 minutes
- **Total Marks:** 19

### Questions
- **Q1–Q4:** MCQ (1 mark each) = 4 marks
- **Q5–Q8:** Subjective (3–5 marks each) = 15 marks
- **Total:** 8 questions, 19 marks

### Question Content
- Q1: Arithmetic (2 + 2)
- Q2: Square root (√16)
- Q3: Constants (π)
- Q4: Algebra (3x = 12)
- Q5: Quadratic equations
- Q6: Calculus (derivatives)
- Q7: Geometry (triangle angles)
- Q8: Systems of equations

---

## File Structure

```
Edtech/
├── exam_platform/          # Platform code
│   ├── app.py              # Flask server
│   ├── models.py           # Data models
│   ├── storage.py          # Data storage
│   ├── mock_data.py        # Test questions
│   └── templates/          # HTML pages
├── uploads/                # Student image uploads
├── test_exam_platform.py   # Automated tests
└── requirements.txt        # Python dependencies
```

---

## First Test Run

### Scenario: Taking a 5-Minute Test

1. **Start:** http://localhost:5000 → "Start Test"
2. **Q1:** Answer "What is 2 + 2?" → B) 4 → Next
3. **Q2:** Answer "√16?" → C) 4 → Next
4. **Q3:** Answer "π?" → A) 3.14 → Next
5. **Q4:** Answer "3x=12?" → D) 4 → Next
6. **Q5:** 
   - Select final answer: A)
   - Click upload, select a sample JPG/PNG file
   - Next
7. **Q6–Q8:** Repeat similar steps
8. **Submit:** Click "Submit Test" → Confirm → Done

**Expected Time:** 3–5 minutes

---

## Important Notes

### MVP Limitations
- Data is lost when server restarts (in-memory storage)
- No login/authentication yet (anyone can access)
- Timer is client-side (can be manipulated)
- Images stored locally (not backed up)

### This IS Suitable For
- ✓ Student testing and feedback
- ✓ UI/UX validation
- ✓ Workflow verification
- ✓ Demo to stakeholders

### This is NOT Suitable For
- ✗ High-stakes exams (needs security)
- ✗ Long-term data storage (no database)
- ✗ Production deployment (no auth)
- ✗ Large user base (single server)

---

## Next Steps

1. **Test Locally:** Use the platform at http://localhost:5000
2. **Collect Feedback:** Try the student workflow, note issues
3. **Verify Features:** Check timer, navigation, upload, submission
4. **Plan Next Phase:** 
   - Add database if needed
   - Connect real question bank
   - Deploy to cloud
   - Add more features

---

## Support & Help

### Check Documentation
- EXAM_PLATFORM_REPORT.md — Complete platform overview
- PLATFORM_VERIFICATION.md — Testing results
- exam_platform/app.py — Source code with comments

### Debug Information
- Server logs show request details
- Browser console (F12) shows JavaScript errors
- Check file permissions in /uploads/ directory

---

**Platform Ready to Use:** http://localhost:5000

**Happy Testing!**
