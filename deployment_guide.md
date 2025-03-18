# Texas Auction Deployment Guide

This guide provides step-by-step instructions for deploying the Texas Auction application on Render with a PostgreSQL database.

## Prerequisites

- GitHub account with access to the repository
- Render account
- Basic understanding of web application deployment

## Step 1: Set Up PostgreSQL Database on Render

1. Log in to your Render dashboard
2. Click on "New +" and select "PostgreSQL"
3. Configure your PostgreSQL database:
   - **Name**: texas-auction-db
   - **Database**: texas_auction
   - **User**: (Render will generate this)
   - **Region**: Choose the region closest to your users
   - **Plan**: Free (or select a paid plan for production use)
4. Click "Create Database"
5. Once created, note the "Internal Database URL" - you'll need this for the web service

## Step 2: Deploy Web Service on Render

1. In your Render dashboard, click on "New +" and select "Web Service"
2. Connect your GitHub repository (https://github.com/meca42/texas-auction)
3. Configure your web service:
   - **Name**: texas-auction
   - **Environment**: Python
   - **Region**: Same as your database
   - **Branch**: main (or your preferred branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
   - **Plan**: Free (or select a paid plan for production use)
4. Add the following environment variables:
   - `DATABASE_URL`: (Paste the Internal Database URL from Step 1)
   - `DEBUG`: `False`
   - `SCRAPE_INTERVAL_DAYS`: `3`
5. Click "Create Web Service"

## Step 3: Initialize the Database

After the web service is deployed:

1. Go to your Web Service dashboard
2. Click on the "Shell" tab
3. Run the following commands to initialize the database:

```bash
# Create database tables
python -c "from database.database import AuctionDatabase; db = AuctionDatabase(); db.create_tables()"

# Import initial data
python import_data.py
```

## Step 4: Set Up Scheduler (Optional)

For automatic data updates every 3 days:

1. In your Render dashboard, click on "New +" and select "Background Worker"
2. Connect to the same GitHub repository
3. Configure your background worker:
   - **Name**: texas-auction-scheduler
   - **Environment**: Python
   - **Region**: Same as your web service
   - **Branch**: main (or your preferred branch)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python scheduler.py`
   - **Plan**: Free (or select a paid plan for production use)
4. Add the same environment variables as the web service
5. Click "Create Background Worker"

## Step 5: Verify Deployment

1. Once deployment is complete, click on the URL provided by Render to access your application
2. Verify that the application loads correctly
3. Check that auction data is displayed properly
4. Test the search and filtering functionality

## Troubleshooting

If you encounter issues:

1. **Database Connection Issues**:
   - Check the Render logs for error messages
   - Verify that the DATABASE_URL environment variable is set correctly
   - Ensure the database service is running

2. **Missing Data**:
   - Verify that the database tables were created successfully
   - Check that the import_data.py script ran without errors
   - Run the import_data.py script manually if needed

3. **Application Errors**:
   - Check the application logs in the Render dashboard
   - Verify that all required environment variables are set
   - Check for any Python exceptions or errors

## Maintenance

- **Database Backups**: Render automatically backs up your PostgreSQL database daily
- **Updates**: Push changes to your GitHub repository, and Render will automatically redeploy
- **Monitoring**: Use the Render dashboard to monitor your application's performance and logs

## Additional Resources

- [Render Documentation](https://render.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Flask Documentation](https://flask.palletsprojects.com/)
