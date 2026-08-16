import numpy as np
import scipy.sparse as sparse
from implicit.als import AlternatingLeastSquares

def test_implicit_als():
    print("Testing implicit.als.AlternatingLeastSquares import... PASS")
    
    # Toy dataset: 3 users, 4 items
    # User 0 likes item 0 and 1
    # User 1 likes item 1 and 2
    # User 2 likes item 3
    
    # Rows = users, Cols = items
    # Confidence matrix = 1 + alpha * interaction_weight
    
    users = [0, 0, 1, 1, 2]
    items = [0, 1, 1, 2, 3]
    weights = [1.0, 1.0, 1.0, 1.0, 1.0]
    
    user_item_matrix = sparse.csr_matrix((weights, (users, items)), shape=(3, 4))
    
    # implicit ALS expects item-user matrix for training
    item_user_matrix = user_item_matrix.T.tocsr()
    
    print(f"Matrix constructed: shape {user_item_matrix.shape}")
    
    # Train
    model = AlternatingLeastSquares(factors=2, regularization=0.01, iterations=10, random_state=42)
    model.fit(item_user_matrix)
    print("Training toy model... PASS")
    
    print(f"User 0 liked items: {user_item_matrix[0].indices}")
    # implicit ALS expects item-user matrix for training, but recommend expects user_item_matrix!
    # Implicit recommend requires the 1 row for the scalar user
    recommendations, scores = model.recommend(0, user_item_matrix[0], N=1, filter_already_liked_items=True)
    print("Scores:", scores)
    
    print(f"Recommendations for User 0 (should exclude 0 and 1): {recommendations}")
    
    assert len(recommendations) == 1
    assert 0 not in recommendations
    assert 1 not in recommendations
    print("Recommendation Generation... PASS")
    
    print("\nALL PRE-FLIGHT CHECKS PASSED.")

if __name__ == "__main__":
    test_implicit_als()
