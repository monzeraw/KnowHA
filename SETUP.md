# Quick Setup Guide

## On Another Machine

### 1. Clone the Repository
```bash
git clone https://github.com/monzeraw/KnowHA.git
cd KnowHA
```

### 2. Install Python Dependencies
```bash
pip3 install -r requirements.txt
```

### 3. Set Up Environment Variables
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

Add your keys:
```
OPENAI_API_KEY=your-actual-openai-api-key
FLASK_SECRET_KEY=your-secret-key
```

### 4. Run the Application
```bash
python3 app.py
```

Open browser: http://127.0.0.1:5002

## Making Changes

### 1. Create a New Branch (Best Practice)
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
Edit files as needed...

### 3. Commit Your Changes
```bash
git add .
git commit -m "Description of your changes"
```

### 4. Push to GitHub
```bash
git push origin feature/your-feature-name
```

### 5. Create Pull Request (Optional)
Go to GitHub and create a pull request to merge into main

## Or Work Directly on Main

### 1. Pull Latest Changes
```bash
git pull origin main
```

### 2. Make Changes and Commit
```bash
git add .
git commit -m "Your changes"
git push origin main
```

## Syncing Between Machines

### Before Starting Work (Pull Latest)
```bash
git pull origin main
```

### After Finishing Work (Push Changes)
```bash
git add .
git commit -m "Your changes"
git push origin main
```

## Troubleshooting

### If you get merge conflicts:
```bash
git pull origin main
# Resolve conflicts in your editor
git add .
git commit -m "Resolved merge conflicts"
git push origin main
```

### To see what changed:
```bash
git status
git diff
```

### To discard local changes:
```bash
git reset --hard origin/main
```
