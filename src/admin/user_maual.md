## Admin Panel User Manual 

1. Introduction
- [Purpose of the Admin Panel](#purpose-of-the-admin-panel)
- [Key Features Overview](#key-features-overview)
- [Who Should Use This Manual](#who-should-use-this-manual)
2. Getting Started
- [Accessing the Admin Panel](#accessing-the-admin-panel)
- [Supported Browsers and Devices](#supported-browsers-and-devices)
- [Overview of the Main Interface](#overview-of-the-main-interface)
3. Dashboard Overview
- [Layout Explanation](#layout-explanation)
- [Navigation Tips](#navigation-tips)
4. Uploading Files
- [Supported File Types](#supported-file-types)
- [How to Upload Files](#how-to-upload-files)
- [Managing Uploaded Files](#managing-uploaded-files)
5. Bot Configuration
- [Selecting a Collection](#selecting-a-collection)
- [Creating a New Collection](#creating-a-new-collection)
- [Setting the Collection Name](#setting-the-collection-name)
- [Changing the Welcome Message](#changing-the-welcome-message)
- [Enabling Key Protection](#enabling-key-protection)
- [Saving Bot Settings](#saving-bot-settings)
- [Changing Bot Name](#changing-bot-name)
6. URL Scraper
- [Purpose of the URL Scraper](#purpose-of-the-url-scraper)
- [How to Enter and Scrape a URL](#how-to-enter-and-scrape-a-url)
- [Managing Scraped Data](#managing-scraped-data)
7. Managing Collections
- [How to Select an Existing Collection](#how-to-select-an-existing-collection)
- [Creating and Deleting Collections](#creating-and-deleting-collections)
- [Best Practices for Organizing Data Sources](#best-practices-for-organiszing-data-sources)
8. Files Management
- [Viewing Uploaded Files](#viewing-uploaded-files)
- [Deleting or Replacing Files](#deleting-or-replacing-files)
- [File Status and Troubleshooting Uploads](#file-status-and-troubleshooting-uploads)
9. Common Tasks & Workflows
- [Example: Setting Up a New Data Source](#example-setting-up-a-new-data-source)
- [Example: Configuring a Bot for a New Department](#example-configuring-a-bot-for-a-new-department)
- [Example: Updating the Welcome Message](#example-updating-the-welcome-message)
10. Troubleshooting & FAQs
- [Common Issues and Solutions](#common-issues-and-solutions)
- [Contacting Support](#contacting-support)
- [Difference Bot Name and Collection Name](#difference-bot-name-and-collection-name)
11. Security & Best Practices
- [Enabling and Managing Key Protection](#enabling-and-managing-key-protection)
- [Data Privacy Guidelines](#data-privacy-guidelines)

## Purpose of the Admin Panel
The Admin Panel provides a centralized interface for administrators to manage InfoBot's data sources, configure chatbot settings, upload and organize files, and monitor system activity. It streamlines the process of maintaining and updating your InfoBot's knowledge base and settings.

## Key Features Overview
- Upload and manage files (txt, pdf, csv) for chatbot training
- Configure bot settings, including welcome messages
- Create, select, and manage data collections
- Scrape and import data from URLs
- View and edit file chunks for granular data management
- Secure sensitive data with key protection
- Manage user (change password, delete user)

## Who Should Use This Manual
This manual is intended for administrators and technical users responsible for managing InfoBot's data sources, configuration, and security settings. Basic familiarity with web applications is recommended.

## Accessing the Admin Panel
- Open your web browser and navigate to the Admin Panel URL (e.g., `http://kit.informatik.fh-nuernberg.de:9090/admin/login`).
- Log in with your administrator credentials.
- If you do not have access, contact the system administrator.

## Supported Browsers and Devices
- The Admin Panel is optimized for modern browsers such as Chrome, Firefox, and Edge.
- For the best experience, use a desktop or laptop device.

## Overview of the Main Interface
- **Top Bar:** Displays the current user name, InfoBot name, collection dropdown, and user actions (create collection, change password, logout).
- **Main Content Area:** Contains panels for file upload, bot configuration, URL scraping, and file management.

## Layout Explanation
- **Upload Files Panel:** Drag and drop or click to upload supported files (txt, pdf, csv).
- **Bot Configuration Panel:** Set the collection name, welcome message, and enable key protection.
- **URL Scraper Panel:** Enter one or more URLs to scrape and import data.
- **Files Panel:** View, edit, or delete uploaded files. Click a file to view and edit its content in chunks.

## Navigation Tips
- Use the top-right menu for user actions (change password, delete user, logout).
- Select a collection via the dropdown in the top bar before configuring bot settings or uploading files.

## Supported File Types
You can upload the following file types as data sources:
- Text files (`.txt`)
- PDF documents (`.pdf`)
- CSV files (`.csv`)

## How to Upload Files
1. Select the collection you want to upload files to using the collection dropdown in the top bar.
2. Go to the **Upload Files** panel on the dashboard.
3. Drag and drop your file(s) into the upload area, or click the area to select files from your computer. You can upload multiple files at a time.
4. Click the `Vectorize` button to upload the files.
5. Wait for the upload to complete. Supported files will appear in the **Files** panel below.

## Managing Uploaded Files
- Uploaded files are listed in the **Files** panel.
- Click a file name to view and edit its content in chunks.
- Use the trash icon to delete a file.
- If a file fails to upload, check the file type and size, then try again. Uploading can take several minutes depending on file size.

## Selecting a Collection
- Use the dropdown menu in the top bar to select an existing collection. The selected collection determines which data source the bot will use.

## Creating a New Collection
1. Click the **Create Collection** button in the top bar.
2. Enter a `Collection Name` for the new collection. This name will be shown in the widget under the `Wissensbasis auswählen` dropdown.
3. Enter a `Welcome Message` for the new collection. This message is the initial message the bot sends to the user upon selecting the collection.
4. Confirm with `Add Collection` to create and switch to the new collection.

## Setting the Collection Name
- The collection name is displayed in the **Bot Configuration** panel.
- To change the name, edit the text in the text box and click `Save Bot Settings` at the bottom of the **Bot Configuration** section.
- Wait for the pop-up that says `Bot settings saved successfully!`.

## Changing the Welcome Message
- Enter a custom welcome message in the **Welcome Message** field in the **Bot Configuration** panel and click `Save Bot Settings`.
- Wait for the pop-up that says `Bot settings saved successfully!`.
- This message will be shown to users when they interact with the bot.

## Enabling Key Protection
- Check the **Enable Key Protection** box in the **Bot Configuration** panel.
- Enter a secure key in the **Data Source Key** field.
- Click `Save Bot Settings` to apply key protection.
- To disable, uncheck the box and save settings again.
- A collection with key protection enabled will only be accessible by entering the corresponding key after pressing `Key` in the `Wissensbasis auswählen` dropdown of the widget.

## Saving Bot Settings
- After making changes to the collection name, welcome message, or key protection, click **Save Bot Settings**.
- A confirmation (`Bot settings saved successfully!`) will appear when settings are saved successfully.

## Changing Bot Name
- Click the pencil icon to the right of the bot name in the top bar.
- A pop-up will appear. Edit the bot name and confirm your changes.

## Purpose of the URL Scraper
The URL Scraper allows you to import data from web pages directly into your collection, making it easy to expand your bot's knowledge base.

## How to Enter and Scrape a URL
1. Go to the **URL Scraper** panel.
2. Enter the desired URL in the input field.
3. To add additional URLs, click the plus sign on the right and enter the URL in the new field.
4. Click the **Scrape** button to import data from the page(s).
5. Wait for the confirmation message to appear.
6. Scraped data will be added to your current collection.

## Managing Scraped Data
- Scraped data appears in the **Files** panel.
- Review and edit imported content as needed.

## How to Select an Existing Collection
- Use the collection dropdown in the top bar to switch between collections. The dashboard will update to reflect the selected collection's files and settings.

## Creating and Deleting Collections
- To create: Click **Create Collection**, enter a collection name and welcome message, and confirm.
- To delete: In the **Bot Configuration** panel, click the three-dot menu and select **Delete Collection**. Confirm the deletion.

## Best Practices for Organizing Data Sources
- Use descriptive names for collections (e.g., department, topic).
- Keep related files grouped in the same collection.
- Regularly review and clean up unused collections and files.

## Viewing Uploaded Files
- All uploaded files are listed in the **Files** panel.
- Click a file to view its content, divided into chunks.
  - You will be directed to a new page displaying all chunks corresponding to the selected file.
  - Edit a chunk by selecting `Edit` in the top right, then click `Save Changes` and confirm.
  - To return to the main page, click the `Back to Admin Panel` button in the top bar.

## Deleting or Replacing Files
- Click the trash icon next to a file to delete it.
- To replace a file, delete the old version and upload the new one.

## File Status and Troubleshooting Uploads
- If a file fails to upload, ensure it is a supported type and not corrupted.
- Check your internet connection and try again.
- For persistent issues, contact support.

## Example: Setting Up a New Data Source
1. Create a new collection for your data source.
2. Upload relevant files (txt, pdf, csv).
3. Configure the bot's welcome message and key protection as needed.
4. Save settings and verify the bot responds with the new data.

## Example: Updating the Welcome Message
1. Select the relevant collection.
2. Edit the welcome message in the **Bot Configuration** panel.
3. Save bot settings.

## Common Issues and Solutions
- **File upload fails:** Check file type and size, and ensure a stable internet connection.
- **Cannot create collection:** Ensure the name is unique and not empty. Ensure the welcome message is not empty.
- **Bot not responding to new data:** Confirm files are uploaded to the correct collection and settings are saved. Reload the page if necessary.

## Contacting Support
- If you encounter issues not covered in this manual, contact your system administrator or support team for assistance.

## Difference Bot Name and Collection Name
- **Bot Name:** The Bot Name, displayed in the top bar next to the user name, is the name of the bot shown in the top center of the widget. It is consistent across all collections for a user.
- **Collection Name:** The Collection Name is the name the user selects in the `Wissensbasis auswählen` dropdown of the widget.

## Enabling and Managing Key Protection
- Use key protection to restrict access to sensitive data sources.
- Store keys securely and share them only with authorized users.
- Update or revoke keys as needed to maintain security.

## Data Privacy Guidelines
- Only upload files that comply with your organization's data privacy policies.
- Regularly review and remove outdated or unnecessary data.
- Ensure sensitive information is removed before uploading to a collection.