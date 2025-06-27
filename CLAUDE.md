# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **OneSilaMagento2Api** - a Python package that wraps and extends the Magento 2 REST API. It's a fork of the `my-magento` package, customized for OneSila's needs. The package provides a comprehensive, user-friendly interface for interacting with all Magento 2 API endpoints.

## Architecture

The codebase follows a **Manager-Model pattern** with three main layers:

### Client Layer (`magento/clients.py`)
- **Client class**: Handles all API authentication, HTTP requests, and provides access to managers
- Supports both password-based and token authentication
- Environment variable configuration support
- Multi-store view support

### Manager Layer (`magento/managers/`)
- Each API endpoint has a dedicated manager (ProductManager, OrderManager, etc.)
- Handles CRUD operations, search queries, and business logic
- Supports advanced operations like `get_or_create`
- Built-in search functionality with filters and criteria

### Model Layer (`magento/models/`)
- **Model**: Standard models that can be created and modified
- **FetchedOnlyModel**: Read-only models (cannot be created directly)
- **ImmutableModel**: Cannot be modified after creation
- Wraps API responses and provides endpoint-specific methods

## Development Commands

### Package Management
```bash
# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Install documentation dependencies
pip install -r docs/requirements.txt
```

### Testing
```bash
# Run all tests using Python's unittest framework
python -m unittest discover tests

# Run specific test module
python -m unittest tests.models.test_products

# Run individual test class
python -m unittest tests.models.test_products.TestProduct
```

### Documentation
```bash
# Build documentation locally
cd docs
make html

# View built documentation
open build/html/index.html
```

### Environment Setup
Create a `.env` file in the project root with the following variables:
```bash
MAGENTO_DOMAIN=your-magento-domain.com
MAGENTO_USERNAME=your-username
MAGENTO_PASSWORD=your-password
MAGENTO_API_KEY=your-api-key  # For token authentication
MAGENTO_AUTH_METHOD=TOKEN     # or PASSWORD
MAGENTO_LOCAL=false           # Set to true for local Magento installations
MAGENTO_USER_AGENT=custom-agent  # Optional custom user agent
```

## API Endpoints and Structure

### Supported Endpoints
- **Orders**: `api.orders` (OrderManager → Order model)
- **Products**: `api.products` (ProductManager → Product model)
- **Categories**: `api.categories` (CategoryManager → Category model)
- **Customers**: `api.customers` (CustomerManager → Customer model)
- **Invoices**: `api.invoices` (InvoiceManager → Invoice model)
- **Shipments**: `api.shipments` (ShipmentManager → Shipment model)
- **Coupons**: `api.coupons` (CouponManager → Coupon model)
- **Sales Rules**: `api.sales_rules` (SalesRuleManager → SalesRule model)
- **Product Attributes**: `api.product_attributes` (ProductAttributeManager → ProductAttribute model)
- **Attribute Sets**: `api.attribute_sets` (AttributeSetManager → AttributeSet model)

### Manager Common Methods
- `by_id(id)`: Retrieve single item by ID
- `search()`: Build and execute search queries
- `create(data)`: Create new resource
- `get_or_create(data, identifier)`: Get existing or create new
- `add_criteria(field, value, condition)`: Add search criteria
- `since(date)`, `until(date)`: Date range filters

### CouponManager Specialized Methods
#### Core Retrieval Methods
- `by_code(code)`: Retrieve coupon by code
- `by_codes(codes)`: Retrieve multiple coupons by codes
- `list_for_rule(rule_id, primary_only=None)`: List all coupons for a sales rule
- `list_codes_for_rule(rule_id, primary_only=None)`: Get coupon code strings for a rule

#### Coupon Lifecycle Management
- `generate(rule_id, qty, length, ...)`: Auto-generate coupon codes
- `create_specific_coupon(rule_id, coupon_code)`: Create specific coupon for a rule
- `update_specific_coupon(coupon_id, updates)`: Update coupon by ID
- `delete_coupon(coupon_id)`: Delete single coupon by ID
- `delete_by_codes(codes)`: Bulk delete by coupon codes
- `delete_by_ids(ids)`: Bulk delete by coupon IDs

#### Status & Analytics Methods
- `active_coupons()`: Get non-expired, non-exhausted coupons
- `expired_coupons()`: Get expired coupons
- `exhausted_coupons()`: Get coupons that reached usage limit
- `expiring_soon(days=7)`: Get coupons expiring within N days
- `created_between(start, end)`: Get coupons created in date range
- `most_used(limit=10)`: Get most frequently used coupons
- `unused()`: Get coupons that have never been used
- `by_usage_range(min_uses, max_uses)`: Get coupons within usage range
- `usage_statistics(rule_id=None)`: Get usage analytics
- `count()`: Total number of coupons
- `count_by_rule(rule_id)`: Number of coupons for specific rule

#### Enhanced Model Properties (Coupon class)
- `remaining_uses`: Number of uses remaining before limit
- `is_exhausted`: Whether coupon reached usage limit
- `is_expired`: Whether coupon is expired
- `days_remaining`: Days until expiration
- `rule`: Get associated cart price rule
- `get_rule()`: Retrieve cart price rule for this coupon

## Authentication

Two authentication methods are supported:

### Password Authentication
```python
import magento
api = magento.get_api(
    domain='your-domain.com',
    username='username',
    password='password',
    authentication_method='PASSWORD'
)
```

### Token Authentication
```python
import magento
api = magento.get_api(
    domain='your-domain.com',
    api_key='your-api-key',
    authentication_method='TOKEN'
)
```

## Key Conventions

- Environment variables are prefixed with `MAGENTO_`
- All managers inherit from the base `Manager` class
- All models inherit from `Model`, `FetchedOnlyModel`, or `ImmutableModel`
- API responses are wrapped in model classes with additional methods
- Search queries use a fluent interface pattern
- Error handling uses custom exception classes in `exceptions.py`

## Testing Environment

Tests use the `unittest` framework with environment variable configuration. The `TestModelMixin` class provides common setup for API client initialization across test classes.

To run tests, ensure your `.env` file contains valid Magento credentials and endpoint information.