# Streamlit Cloud Deployment Guide

## Prerequisites
✅ Your code is already on GitHub: `tavaresieta/ieta-prep-tools`
✅ `requirements.txt` is ready
✅ Main app file: `meeting_prep.py`

## Step-by-Step Deployment

### 1. Push Latest Changes to GitHub
```powershell
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### 2. Deploy on Streamlit Cloud

1. **Go to Streamlit Cloud:**
   - Visit: https://share.streamlit.io/
   - Sign in with your GitHub account

2. **Create New App:**
   - Click "New app"
   - Select your repository: `tavaresieta/ieta-prep-tools`
   - Branch: `main`
   - Main file path: `meeting_prep.py`
   - Click "Deploy"

3. **Wait for Deployment:**
   - Streamlit Cloud will:
     - Install dependencies from `requirements.txt`
     - Run your app
     - Provide a public URL (e.g., `https://ieta-prep-tools.streamlit.app/`)

### 3. Configure Secrets (API Keys)

After deployment, add your Anthropic API key:

1. Go to your app settings in Streamlit Cloud
2. Click "Secrets" in the sidebar
3. Add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   ```
4. Save and restart the app

### 4. Upload Documents and Metadata

Your app needs:
- `documents/` folder with `.txt` files
- `metadata/` folder with keyword files

**Option A: Commit to GitHub** (if files are small)
```powershell
git add documents/ metadata/
git commit -m "Add documents and metadata"
git push origin main
```

**Option B: Use Streamlit's file uploader** (if you add this feature)

**Option C: Use external storage** (S3, Google Drive, etc.)

## Important Notes

⚠️ **File Size Limits:**
- Streamlit Cloud has file size limits
- Large documents may need external storage

⚠️ **Metadata Files:**
- Make sure `metadata/keywords_metadata.json` and `metadata/keywords_metadata_index.json` are committed
- Or regenerate them after deployment using `process_and_sync.py --keywords-only`

## Troubleshooting

**App won't start:**
- Check logs in Streamlit Cloud dashboard
- Verify `requirements.txt` has all dependencies
- Ensure `meeting_prep.py` is the correct main file

**Documents not loading:**
- Verify `documents/` folder exists in GitHub
- Check file paths in code (should be relative)

**Keywords not working:**
- Ensure metadata files are in `metadata/` folder
- Run keyword extraction if needed

## Your App URL
Once deployed, your app will be available at:
`https://ieta-prep-tools.streamlit.app/`

Share this URL with your colleagues! 🌍
