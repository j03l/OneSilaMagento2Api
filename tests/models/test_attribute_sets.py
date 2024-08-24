import unittest
from magento.models import AttributeSet, ProductAttribute
from tests.mixins import TestModelMixin

class TestProductAttributeSetModel(TestModelMixin, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a base attribute set to use in tests
        cls.skeleton_id = 4

        # Create a product attribute to be used in the attribute set
        attribute_data = {
            "attribute_code": "test",
            "frontend_input": ProductAttribute.SELECT,
            "default_frontend_label": "Test attr"
        }
        cls.attribute = ProductAttribute(data=attribute_data, client=cls.api)
        cls.attribute.save()
        cls.class_to_delete.append(cls.attribute)

    def test_get_attribute_set(self):
        # TEST GET and Operations on the Attribute Set

        # Step 1: Create a new attribute set
        attribute_set = AttributeSet(data={
            "attribute_set_name": "Attribute Set",
            "sort_order": 10,
            "skeleton_id": self.skeleton_id
        }, client=self.api)
        attribute_set.save()
        attribute_set.refresh()

        self.register_for_deletion(attribute_set)

        # Step 2: Create an Attribute Group within the Attribute Set
        group = attribute_set.create_group('Test Group')
        self.assertIsNotNone(group)
        self.assertEqual(group.attribute_group_name, 'Test Group')

        # Step 3: Add an Attribute to the created Attribute Set under the 'Test Group'
        attribute_set.add_attribute_set_attribute(group.attribute_group_id, self.attribute.attribute_code, 1)

        # Fetch and validate
        fetched_attribute_set = self.api.product_attribute_set.by_id(attribute_set.attribute_set_id)
        self.assertIsNotNone(fetched_attribute_set)
        self.assertEqual(fetched_attribute_set.attribute_set_name, 'Attribute Set')

    def test_create_attribute_set_via_create_method(self):
        # TEST CREATE VIA CREATE METHOD
        create_data = {
            "attribute_set_name": "Test Attribute Set via Create",
            "sort_order": 10,
            "skeleton_id": self.skeleton_id
        }
        created_attribute_set = self.api.product_attribute_set.create(data=create_data)

        self.register_for_deletion(created_attribute_set)

        # Assertions
        self.assertEqual(created_attribute_set.attribute_set_name, "Test Attribute Set via Create")
        self.assertEqual(created_attribute_set.sort_order, 10)

    def test_create_attribute_set_via_initialization(self):
        # TEST CREATE VIA INITIALIZING ATTRIBUTE SET AND ADD PARAMETERS THEN SAVE
        attribute_set = AttributeSet(data={}, client=self.api)
        attribute_set.attribute_set_name = 'Initialized Attribute Set'
        attribute_set.sort_order = 15
        attribute_set.skeleton_id = self.skeleton_id
        attribute_set.save()

        self.register_for_deletion(attribute_set)

        # Assertions
        self.assertEqual(attribute_set.attribute_set_name, 'Initialized Attribute Set')
        self.assertEqual(attribute_set.sort_order, 15)

    def test_update_attribute_set(self):
        # Create a new attribute set to update
        attribute_set = AttributeSet(data={}, client=self.api)
        attribute_set.attribute_set_name = 'Attribute Set to Update'
        attribute_set.sort_order = 20
        attribute_set.skeleton_id = self.skeleton_id
        attribute_set.save()

        self.register_for_deletion(attribute_set)

        # TEST UPDATE VIA SAVE
        attribute_set_to_update = self.api.product_attribute_set.by_id(attribute_set.attribute_set_id)
        attribute_set_to_update.attribute_set_name = "Updated Attribute Set Name"
        attribute_set_to_update.save()

        # Refresh and assert
        attribute_set_to_update.refresh()
        self.assertEqual(attribute_set_to_update.attribute_set_name, "Updated Attribute Set Name")

    def test_delete_attribute_set(self):
        # Create a new attribute set to delete
        attribute_set = AttributeSet(data={}, client=self.api)
        attribute_set.attribute_set_name = 'Attribute Set to Delete'
        attribute_set.sort_order = 25
        attribute_set.skeleton_id = self.skeleton_id
        attribute_set.save()

        # TEST DELETE
        result = attribute_set.delete()

        # Assertions
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()