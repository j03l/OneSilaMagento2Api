import magento
from magento import AuthenticationMethod
from dotenv import load_dotenv
import os

load_dotenv()

class TestModelMixin:
    @classmethod
    def setUpClass(cls) -> None:

        domain = os.getenv('MAGENTO_DOMAIN')
        username = os.getenv('MAGENTO_USERNAME')
        password = os.getenv('MAGENTO_PASSWORD')
        api_key = os.getenv('MAGENTO_API_KEY')
        local = os.getenv('MAGENTO_LOCAL', 'False').lower() in ('True', 'true', '1', 't')
        user_agent = os.getenv('MAGENTO_USER_AGENT', None)
        auth_method = os.getenv('MAGENTO_AUTH_METHOD', AuthenticationMethod.TOKEN)

        cls.api = magento.get_api(
            domain=domain,
            username=username,
            password=password,
            api_key=api_key,
            local=local,
            user_agent=user_agent,
            authentication_method=auth_method,
            strict_mode=True
        )

        cls.class_to_delete = []


    def setUp(self) -> None:
        # Initialize a list to track objects to delete after each test
        self.to_delete = []

    @classmethod
    def tearDownClass(cls) -> None:
        for obj in cls.class_to_delete:
            try:
                obj.delete()
            except Exception as e:
                print(f"Failed to delete object: {obj}, error: {e}")


    def tearDown(self) -> None:
        # Delete all objects created during the test
        for obj in self.to_delete:
            try:
                obj.delete()
            except Exception as e:
                print(f"Failed to delete object: {obj}, error: {e}")

    def register_for_deletion(self, obj, class_level=False):
        """Register an object to be deleted during teardown."""
        if class_level:
            self.class_to_delete.append(obj)
        else:
            self.to_delete.append(obj)