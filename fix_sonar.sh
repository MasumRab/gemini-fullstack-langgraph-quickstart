# Fix SonarCloud issues
cd backend

sed -i 's/except Exception as e: # noqa: BLE001/except OSError as e:/' scripts/update_all_notebooks.py
sed -i 's/except Exception as e:/except OSError as e:/' scripts/update_all_notebooks.py

# Remove empty mock_send, call_next if they are not used and are warning triggers, but they are tests.
# The real issue is "Broad exception caught".
# Let's fix exceptions in test_available_models and update_models

sed -i 's/except Exception as e:/except Exception as e:/' scripts/update_notebooks_gemma3.py
# wait, update_notebooks_gemma3 has no try-except.
