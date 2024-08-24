import unittest
from magento.models import Product, ProductAttribute, AttributeOption, ConfigurableProduct
from tests.mixins import TestModelMixin

class TestConfigurableProductModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Step 1: Create a test attribute
        cls.attribute = ProductAttribute(data={"attribute_code": "test_configurable"}, client=cls.api)
        cls.attribute.frontend_input = ProductAttribute.SELECT
        cls.attribute.default_frontend_label = 'Test config  attr'
        cls.attribute.save()
        cls.class_to_delete.append(cls.attribute)

        # Step 2: Create a test attribute set
        create_data = {
            "attribute_set_name": "Configurable Product Attribute Set",
            "sort_order": 10,
            "skeleton_id": 4
        }
        cls.attribute_set = cls.api.product_attribute_set.create(data=create_data)
        cls.class_to_delete.append(cls.attribute_set)

        # Step 3: Create an Attribute Group within the Attribute Set
        cls.group = cls.attribute_set.create_group('Test Group')

        # Step 4: Add the 'test' attribute to the created Attribute Set under the 'Test Group'
        cls.attribute_set.add_attribute_set_attribute(cls.group.attribute_group_id, cls.attribute.attribute_code, 1)

        # Step 5: Create two attribute options for the attribute 'test'. Don't need to add to be deleted since the attribute will be deleted
        cls.option1 = AttributeOption(data={}, attribute=cls.attribute, client=cls.api)
        cls.option1.label = 'Option 1'
        cls.option1.sort_order = 1
        cls.option1.save()

        cls.option2 = AttributeOption(data={}, attribute=cls.attribute, client=cls.api)
        cls.option2.label = 'Option 2'
        cls.option2.sort_order = 2
        cls.option2.save()

    def setUp(self):
        super().setUp()

        # Step 6: Create two simple products
        create_data_1 = {
            "sku": "example-sku-001",
            "name": "Example Product 1",
            "attribute_set_id": self.attribute_set.attribute_set_id,
            "price": 199.99,
            "special_price": 179.99,
            "meta_keyword": "api-test",
        }
        self.product1 = Product(data=create_data_1, client=self.api)
        self.product1.save()

        create_data_2 = {
            "sku": "example-sku-002",
            "name": "Example Product 2",
            "attribute_set_id": self.attribute_set.attribute_set_id,
            "price": 199.99,
            "special_price": 179.99,
            "meta_keyword": "api-test",
            "stock": 10,
            "backorders": False
        }
        self.product2 = Product(data=create_data_2, client=self.api)
        self.product2.save()

        self.register_for_deletion(self.product1)
        self.register_for_deletion(self.product2)

        # make sure we refresh the options before
        self.option1.refresh()
        self.option2.refresh()

        # Associate products with options
        self.product1.update_custom_attributes({'test_configurable': self.option1.uid})
        self.product2.update_custom_attributes({'test_configurable': self.option2.uid})

    def test_create_and_manage_configurable_product(self):
        # Step 7: Create a configurable product
        configurable_data = {
            "sku": "configurable-example-sku",
            "name": "Configurable Example Product",
            "attribute_set_id": self.attribute_set.attribute_set_id,
            "price": 249.99,
            "meta_keyword": "api-test-configurable",
            "stock": 0,
            "type_id": "configurable"
        }
        self.configurable_product = self.api.products.create(data=configurable_data)
        self.register_for_deletion(self.configurable_product)

        # Step 8: Use ConfigurableProduct model to add child products
        configurable_prod = ConfigurableProduct(product=self.configurable_product, client=self.api)

        configurable_prod.add_child(self.product1, [self.attribute])
        configurable_prod.add_child(self.product2, [self.attribute])

        # Refresh and verify that the child products were correctly added
        self.configurable_product.refresh()
        children = self.configurable_product.children
        self.assertEqual(len(children), 2)

        # Validate child products
        child_skus = [child.sku for child in children]
        self.assertIn('example-sku-001', child_skus)
        self.assertIn('example-sku-002', child_skus)

        # Step 9: Test remove_child
        configurable_prod.remove_child(self.product1)
        self.configurable_product.refresh()
        children_after_removal = self.configurable_product.children
        self.assertEqual(len(children_after_removal), 1)
        self.assertNotIn('example-sku-001', [child.sku for child in children_after_removal])


if __name__ == '__main__':
    unittest.main()
