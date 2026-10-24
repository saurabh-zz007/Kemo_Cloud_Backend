from qdrant_client import QdrantClient

# Connect to your self-hosted instance
client = QdrantClient(url="http://localhost:6333")

collection_name = "your_collection_name"

# Check if it exists before trying to delete
if client.collection_exists(collection_name=collection_name):
    # Execute the deletion
    client.delete_collection(collection_name=collection_name)
    print(f"Collection '{collection_name}' successfully deleted.")
else:
    print(f"Collection '{collection_name}' does not exist.")