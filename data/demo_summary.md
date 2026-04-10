# Demo Data Summary

This file explains what demo data will be loaded when installing the Asset Management module with demo data enabled.

## 🎯 What Gets Loaded

### Asset Types (5 types)
1. **Office Equipment** - 20% yearly depreciation
2. **Vehicles** - 25% yearly depreciation  
3. **Office Furniture** - 15% yearly depreciation
4. **Computers & IT** - 33.33% yearly depreciation
5. **Buildings** - 5% yearly depreciation

### Asset Tags (5 tags)
1. **High Value** - For expensive assets
2. **Critical** - For essential business assets
3. **Office** - For office-related assets
4. **Warehouse** - For storage assets
5. **Leased** - For leased assets

### Vendors (4 vendors)
1. **Tech Solutions Inc.** - IT equipment and services
2. **Office Supplies Plus** - Office supplies and equipment
3. **Auto Services & Maintenance** - Vehicle services
4. **Furniture Warehouse Co.** - Office furniture

### Sample Assets (6 assets)

#### Single Assets
- **Laptop** (ASSET/00001) - $1,200, assigned to admin
- **Desk** (ASSET/00002) - $450, in warehouse
- **Vehicle** (ASSET/00003) - $25,000, assigned to admin

#### Multiple Assets (Stock Managed)
- **Office Chairs** (ASSET/00004) - 50 units, $150 each
- **Monitors** (ASSET/00005) - 25 units, $300 each  
- **Printers** (ASSET/00006) - 10 units, $800 each

### Transfer Entries (4 entries)
- Laptop assigned to admin (30 days ago)
- Vehicle assigned to admin (60 days ago)
- 5 chairs assigned to admin (15 days ago)
- 3 monitors assigned to admin (20 days ago)

### Maintenance Records (2 entries)
- Vehicle maintenance completed ($150, 45 days ago)
- Laptop repair in progress ($200, 10 days ago)

### Depreciation Entries (3 entries)
- Laptop: $200 depreciation (1 month ago)
- Vehicle: $6,250 depreciation (1 month ago)
- Desk: $56.25 depreciation (1 month ago)

## 🔍 How to Explore the Demo Data

### 1. Asset Overview
- Go to **Assets > Assets** to see all sample assets
- Use filters to view by type, status, or model type
- Check the status bar to see asset lifecycle

### 2. Asset Types
- Navigate to **Assets > Configuration > Asset Types**
- Review depreciation settings for each type
- See how different rates affect asset values

### 3. Transfer Management
- Open any asset and go to the **Transfer** tab
- See how assets are assigned to employees
- Notice the automatic transfer code generation

### 4. Maintenance Tracking
- Check the **Maintenance** tab on assets
- View maintenance costs and vendor information
- See document attachment capabilities

### 5. Depreciation Calculation
- Review the **Depreciation** tab on assets
- Understand how depreciation affects current values
- See the automated depreciation system in action

### 6. Stock Management
- Focus on multiple assets (chairs, monitors, printers)
- See how stock quantities change with transfers
- Understand the difference between single and multiple assets

## 💡 Learning Objectives

After exploring the demo data, you should understand:

- **Asset Lifecycle**: How assets move through different statuses
- **Depreciation**: How different rates and methods work
- **Stock Management**: Difference between single and multiple assets
- **Transfer Process**: How assets are assigned and returned
- **Maintenance**: How to track repair and service costs
- **Vendor Management**: How to organize supplier information
- **Tagging**: How to categorize and organize assets

## 🚀 Next Steps

1. **Modify Demo Data**: Change values to match your business needs
2. **Add Real Assets**: Create assets based on your actual inventory
3. **Configure Users**: Set up proper user groups and permissions
4. **Customize Types**: Adjust asset types for your industry
5. **Set Up Vendors**: Add your actual suppliers and service providers

## ⚠️ Important Notes

- Demo data is marked with `noupdate="1"` - it won't be overwritten on updates
- All demo assets use realistic but fictional data
- Dates are calculated relative to installation date
- Financial amounts are examples only
- User references point to the admin user (base.user_admin)

---

This demo data provides a complete working example of the Asset Management module's capabilities, making it easy to understand and test all features before implementing in production.
