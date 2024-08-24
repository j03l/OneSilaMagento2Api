import unittest
from magento.models import Product, ProductAttribute, AttributeOption, MediaEntry
from tests.mixins import TestModelMixin

class TestProductModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a common instance for all tests, if needed
        product_data = {
            "sku": "example-fetched-sku-001",
            "name": "Fetched Product",
            "attribute_set_id": 4,
            "price": 99.99,
        }
        cls.instance = Product(data=product_data, client=cls.api)
        cls.instance.save()
        cls.class_to_delete.append(cls.instance)

    def test_create_product_with_initialization(self):
        # TEST CREATE PRODUCT WITH INITIALIZATION
        product_data = {
            "sku": "example-sku-005",
            "name": "Example Product",
            "attribute_set_id": 4, # magento default attributes set is 4
            "price": 99.99,
        }
        product = Product(data=product_data, client=self.api)

        # Add additional properties after initialization
        product.special_price = 79.99
        product.meta_keyword = "test"
        product.stock = 4
        product.backorders = True

        # Save the product
        product.save()

        # Register for deletion
        self.register_for_deletion(product)

        # Assertions
        self.assertEqual(product.sku, "example-sku-005")
        self.assertEqual(product.name, "Example Product")
        self.assertEqual(product.price, 99.99)
        self.assertEqual(product.special_price, 79.99)
        self.assertTrue(product.backorders)
        self.assertEqual(product.stock, 4)

    def test_create_product_via_api(self):
        # TEST CREATE PRODUCT VIA API
        create_data = {
            "sku": "example-sku-002",
            "name": "Another Example Product",
            "attribute_set_id": 4,
            "price": 199.99,
            "special_price": 179.99,
            "meta_keyword": "api-test",
            "stock": 10,
            "backorders": False
        }
        api_created_product = self.api.products.create(data=create_data)

        # Register for deletion
        self.register_for_deletion(api_created_product)

        # Assertions
        self.assertEqual(api_created_product.sku, "example-sku-002")
        self.assertEqual(api_created_product.name, "Another Example Product")
        self.assertEqual(api_created_product.price, 199.99)
        self.assertEqual(float(api_created_product.special_price), float(179.99))
        self.assertEqual(api_created_product.meta_keyword, "api-test")
        self.assertEqual(api_created_product.stock, 10)
        self.assertFalse(api_created_product.backorders)

    def test_retrieve_product_by_sku(self):
        # TEST RETRIEVE PRODUCT BY SKU
        retrieved_product = self.api.products.by_sku('example-fetched-sku-001')

        # Assertions
        self.assertEqual(retrieved_product.sku, "example-fetched-sku-001")
        self.assertEqual(retrieved_product.name, "Fetched Product")

    def test_update_product(self):
        # TEST UPDATE PRODUCT
        retrieved_product = self.api.products.by_sku('example-fetched-sku-001')
        retrieved_product.name = "Updated Example Product"
        retrieved_product.price = 89.99
        retrieved_product.save()

        # Assertions
        self.assertEqual(retrieved_product.name, "Updated Example Product")
        self.assertEqual(retrieved_product.price, 89.99)

    def test_delete_product(self):
        # Step 1: Create a product
        product_data = {
            "sku": "example-sku-delete-001",
            "name": "Delete Test Product",
            "attribute_set_id": 4,
            "price": 59.99,
        }
        product = Product(data=product_data, client=self.api)

        # Save the product
        product.save()

        # Step 2: Delete the product
        delete_result = product.delete()

        # Step 3: Verify the product was deleted
        self.assertTrue(delete_result)
        with self.assertRaises(Exception):
            self.api.products.by_sku('example-sku-003')


class TestProductAttributeModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a common attribute to work with, shared across all tests
        attribute_data = {
            "attribute_code": "test",
            "frontend_input": ProductAttribute.SELECT,
            "default_frontend_label": "Test attr"
        }
        cls.instance = ProductAttribute(data=attribute_data, client=cls.api)
        cls.instance.save()
        cls.class_to_delete.append(cls.instance)

    def test_get_product_attribute_by_code(self):
        # TEST GET
        attribute = self.api.product_attributes.by_code('test')

        # Assertions
        self.assertIsNotNone(attribute)
        self.assertEqual(attribute.attribute_code, 'test')
        self.assertEqual(attribute.default_frontend_label, 'Test attr')

    def test_create_product_attribute_via_create(self):
        # TEST CREATE VIA CREATE
        create_data = {
            "attribute_code": "test_create",
            "frontend_input": ProductAttribute.SELECT,
            "default_frontend_label": 'Test Create Attr'
        }
        attribute = self.api.product_attributes.create(data=create_data)

        # Register for deletion
        self.register_for_deletion(attribute)

        # Assertions
        self.assertEqual(attribute.attribute_code, 'test_create')
        self.assertEqual(attribute.default_frontend_label, 'Test Create Attr')

    def test_create_product_attribute_via_initialization(self):
        # TEST CREATE VIA INITIALIZNG PRODUCT AND ADD PARAMETERS THEN SAVE
        attribute = ProductAttribute(data={"attribute_code": "test_init"}, client=self.api)

        # Setting additional properties
        attribute.frontend_input = ProductAttribute.SELECT
        attribute.default_frontend_label = 'Test Init Attr'
        attribute.is_required = False
        attribute.is_searchable = True
        attribute.is_filterable = False
        attribute.is_comparable = True
        attribute.is_visible_on_front = False

        # Save the attribute
        attribute.save()

        # Register for deletion
        self.register_for_deletion(attribute)

        # Assertions
        self.assertEqual(attribute.attribute_code, 'test_init')
        self.assertEqual(attribute.default_frontend_label, 'Test Init Attr')
        self.assertFalse(attribute.is_required)
        self.assertTrue(attribute.is_searchable)
        self.assertFalse(attribute.is_filterable)
        self.assertEqual(attribute.is_comparable, '1')
        self.assertEqual(attribute.is_visible_on_front, '0')

    def test_update_product_attribute(self):
        # TEST UPDATE VIA SAVE
        attribute = self.api.product_attributes.by_code('test')
        attribute.default_frontend_label = 'New Test Attr'
        attribute.save()

        # Fetch the updated attribute
        updated_attribute = self.api.product_attributes.by_code('test')

        # Assertions
        self.assertEqual(updated_attribute.default_frontend_label, 'New Test Attr')

    def test_delete_product_attribute(self):
        # Create an attribute to delete
        attribute_data = {
            "attribute_code": "test_delete",
            "frontend_input": ProductAttribute.SELECT,
            "default_frontend_label": "Test Delete Attr"
        }
        attribute = ProductAttribute(data=attribute_data, client=self.api)
        attribute.save()

        # Step 2: Delete the attribute
        delete_result = attribute.delete()

        # Step 3: Verify the attribute was deleted
        self.assertTrue(delete_result)
        with self.assertRaises(Exception):
            self.api.product_attributes.by_code('test_delete')

class TestProductAttributeOptionModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a new attribute for this test
        attribute_data = {
            "attribute_code": "test_option",
            "frontend_input": ProductAttribute.SELECT,
            "default_frontend_label": "Test Option attr"
        }
        cls.attribute = ProductAttribute(data=attribute_data, client=cls.api)
        cls.attribute.save()
        cls.class_to_delete.append(cls.attribute)

    def test_create_attribute_option_with_initialization(self):
        # TEST CREATE ATTRIBUTE OPTION WITH INITIALIZATION
        option = AttributeOption(data={}, attribute=self.attribute, client=self.api)
        option.label = 'New Label'
        option.sort_order = 3
        option.save()

        self.register_for_deletion(option)
        self.assertEqual(option.label, 'New Label')
        self.assertEqual(option.sort_order, 3)

    def test_create_attribute_option_via_api(self):
        # TEST CREATE ATTRIBUTE OPTION WITH API
        create_data = {
            "label": "Another New Label",
            "sort_order": 4
        }
        self.api.product_attribute_options_attribute = self.attribute
        option = self.api.product_attribute_options.create(data=create_data)

        self.register_for_deletion(option)
        self.assertEqual(option.label, 'Another New Label')

    def test_update_attribute_option_via_save(self):
        # Create an attribute option first
        option = AttributeOption(data={}, attribute=self.attribute, client=self.api)
        option.label = 'Initial Label'
        option.save()

        # Update the label
        option.label = 'Updated Label'
        option.save()

        # Refresh the option to ensure it's correctly updated
        option.refresh()

        # Assertions
        self.assertEqual(option.label, 'Updated Label')

    def test_delete_attribute_option(self):
        # Create an attribute option first
        option = AttributeOption(data={}, attribute=self.attribute, client=self.api)
        option.label = 'Label to Delete'
        option.save()

        # Refresh the option to ensure it's correctly created
        option.refresh()

        # Delete the option
        result = option.delete()

        # Assertions
        self.assertTrue(result)

class TestMediaEntryModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a product to use in media entry tests
        product_data = {
            "sku": "image-example-sku",
            "name": "Test Product for Media",
            "attribute_set_id": 4,
            "price": 99.99,
        }
        cls.product = Product(data=product_data, client=cls.api)
        cls.product.save()
        cls.class_to_delete.append(cls.product)

        # Set the media_entries_product attribute for API client
        cls.api.media_entries_product = cls.product

    def test_create_media_entry_via_api(self):
        # TEST 1: CREATE VIA CREATE METHOD
        create_data = {
            "image_url": "https://htmlcolorcodes.com/assets/images/colors/bright-blue-color-solid-background-1920x1080.png",
            "label": "Example Image Create",
            "position": 1,
            "disabled": False,
            "media_type": "image",
            "types": ["thumbnail", "small_image"]
        }
        media_entry_create = self.api.product_media_entries.create(data=create_data)

        # Register for deletion
        self.register_for_deletion(media_entry_create)

        # Assertions
        self.assertEqual(media_entry_create.label, "Example Image Create")
        self.assertEqual(media_entry_create.position, 1)
        self.assertEqual(media_entry_create.media_type, "image")
        self.assertSetEqual(set(media_entry_create.types), {"thumbnail", "small_image"})

    def test_create_media_entry_via_initialization(self):
        # TEST 2: CREATE VIA INITIALIZING MEDIAENTRY AND ADD PARAMETERS THEN SAVE
        media_entry = MediaEntry(product=self.product, entry={})
        media_entry.data['image_url'] = "https://htmlcolorcodes.com/assets/images/colors/bright-blue-color-solid-background-1920x1080.png"
        media_entry.label = "Initialized Media Entry"
        media_entry.position = 2
        media_entry.types = ["thumbnail", 'small_image', 'image']
        media_entry.media_type = "image"
        media_entry.save()
        media_entry.refresh()

        # Register for deletion
        self.register_for_deletion(media_entry)

        # Assertions
        self.assertEqual(media_entry.label, "Initialized Media Entry")
        self.assertEqual(media_entry.position, 2)
        self.assertEqual(media_entry.media_type, "image")
        self.assertSetEqual(set(media_entry.types), {"thumbnail", "small_image", "image"})

    def test_update_media_entry(self):
        # Create a media entry to update
        media_entry_data = {
            "image_url": "https://htmlcolorcodes.com/assets/images/colors/bright-blue-color-solid-background-1920x1080.png",
            "label": "Test Media Entry",
            "position": 1,
            "disabled": False,
            "media_type": "image",
            "types": ["thumbnail", "small_image"]
        }
        media_entry_to_update = self.api.product_media_entries.create(data=media_entry_data)
        self.register_for_deletion(media_entry_to_update)

        # Update the media entry
        media_entry_to_update.label = "Updated Media Entry"
        media_entry_to_update.position = 3
        media_entry_to_update.save()

        # Refresh the media entry
        media_entry_to_update.refresh()

        # Assertions
        self.assertEqual(media_entry_to_update.label, "Updated Media Entry")
        self.assertEqual(media_entry_to_update.position, 3)

    def test_delete_media_entry(self):
        # Create a media entry to delete
        media_entry_data = {
            "image_url": "https://htmlcolorcodes.com/assets/images/colors/bright-blue-color-solid-background-1920x1080.png",
            "label": "Test Media Entry",
            "position": 1,
            "disabled": False,
            "media_type": "image",
            "types": ["thumbnail", "small_image"]
        }
        media_entry_to_delete = self.api.product_media_entries.create(data=media_entry_data)

        # Delete the media entry
        result = media_entry_to_delete.delete()

        # Assertions
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
