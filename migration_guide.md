# Texas Auction Database Migration Guide

This guide provides detailed instructions for migrating the Texas Auction application from SQLite to PostgreSQL for deployment on Render.

## Migration Overview

The Texas Auction application has been modified to support both SQLite (for development) and PostgreSQL (for production on Render). The key changes include:

1. **Database Abstraction Layer**: The database code now supports both SQLite and PostgreSQL connections
2. **Environment-Based Configuration**: Database connection is now configured via environment variables
3. **PostgreSQL Compatibility**: SQL queries have been updated to work with both database systems
4. **Deployment Documentation**: Comprehensive guides for deploying on Render

## Migration Steps

### 1. Update Dependencies

The following dependencies have been added to `requirements.txt`:
- `psycopg2-binary`: PostgreSQL adapter for Python
- `python-dotenv`: For loading environment variables

### 2. Database Configuration

The application now uses a database URL format for configuration:
- SQLite: `sqlite:///path/to/database.db`
- PostgreSQL: `postgresql://username:password@hostname:port/database`

### 3. Environment Variables

Create a `.env` file based on the provided `.env.example` with the following variables:
- `DATABASE_URL`: Database connection string
- `DEBUG`: Enable/disable debug mode
- `PORT`: Application port
- `SCRAPE_INTERVAL_DAYS`: Data update frequency

### 4. Code Changes

The following files have been modified:
- `database/database.py`: Updated to support both SQLite and PostgreSQL
- `run.py`: Updated to use environment variables
- `wsgi.py`: Updated to load environment variables
- `import_data.py`: No changes needed, works with the updated database layer
- `scheduler.py`: No changes needed, works with the updated database layer

### 5. Testing

Two test scripts have been created:
- `test_db_connection.py`: Tests database connectivity
- `test_app_functionality.py`: Tests full application functionality

### 6. Deployment

Follow the instructions in `deployment_guide.md` for deploying on Render with PostgreSQL.

## SQLite vs PostgreSQL Differences

### Data Types
- SQLite uses dynamic typing, PostgreSQL uses static typing
- `INTEGER PRIMARY KEY` in SQLite becomes `SERIAL PRIMARY KEY` in PostgreSQL
- Date/time handling is more strict in PostgreSQL

### Query Syntax
- Parameter placeholders: SQLite uses `?`, PostgreSQL uses `%s`
- Last inserted ID: SQLite uses `cursor.lastrowid`, PostgreSQL uses `SELECT lastval()`
- Case sensitivity: PostgreSQL is case-sensitive for identifiers

### Transaction Handling
- Both systems support transactions, but PostgreSQL has more advanced features
- Connection pooling is recommended for PostgreSQL in production

## Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Check that the DATABASE_URL is correctly formatted
   - Verify that the PostgreSQL server is running and accessible
   - Check for network restrictions or firewall issues

2. **Migration Errors**:
   - SQLite data doesn't automatically migrate to PostgreSQL
   - Run the import_data.py script to populate the PostgreSQL database

3. **Performance Issues**:
   - PostgreSQL may require index optimization for large datasets
   - Consider connection pooling for high-traffic applications

### Logging

The application logs to the following files:
- `webapp.log`: Web application logs
- `database.log`: Database operation logs
- `import.log`: Data import logs
- `scheduler.log`: Scheduler logs
- `db_test.log`: Database test logs
- `app_test.log`: Application test logs

## Reverting to SQLite

If needed, you can revert to SQLite by:
1. Setting `DATABASE_URL=sqlite:///database/texas_auctions.db` in your `.env` file
2. Restarting the application

This is recommended only for development purposes, not for production use on Render.
