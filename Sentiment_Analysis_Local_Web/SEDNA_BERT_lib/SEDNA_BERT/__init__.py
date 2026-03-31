"""
SEDNA_BERT_Library
An end-to-end BERT framework for training/testing with interchangeable models:
 - BERT
 - RoBERTa
 - DeBERTa
"""

# =========================
# 1. Export Core API
# =========================
from .core_code import (
    # Model
    Sentiment_Analysis,

    # Tokenization & DataLoader
    Apply_Tokenization,
    get_data_loader,
    Train_Validate_Test_Loader,

    # Optimiser / Device / Training Setup
    X_Entropy_Hypersetting,

    # Training loop
    iterative_train,
    iterative_evaluate,
    Training_loop,

    # Visualization
    Visualisation,

    # Evaluation / Test / Reload
    Test_model,
    Reload_Model,

    # Utils
    get_accuracy,

    # Evaluation
    Confusion_matrix_ROC,
    Misclassification,

    # Prediction
    Sentiment_Classification
)

__all__ = [
    # Model
    "Sentiment_Analysis",

    # Tokenization & DataLoader
    "Apply_Tokenization",
    "get_data_loader",
    "Train_Validate_Test_Loader",

    # Training setup
    "X_Entropy_Hypersetting",

    # Train / Eval
    "iterative_train",
    "iterative_evaluate",
    "Training_loop",

    # Visualization
    "Visualisation",

    # Test / Infer
    "Test_model",
    "Reload_Model",

    # Utility
    "get_accuracy",

    # Evaluation
    "Confusion_matrix_ROC",
    "Misclassification"
    
    # Prediction
    "Sentiment_Classification"
]

#  =============================================================================================

'''
# ✅ 只保留文字欢迎信息（无 Logo），其余逻辑完全不变
import os
from pathlib import Path

try:
    from IPython.display import display, HTML
    _JUPYTER = True
except ImportError:
    _JUPYTER = False

def _show_sedna_welcome():

    html_code = """
    <div style="text-align:center; font-size:16px; font-weight:bold; margin-top:15px;">
        Welcome back to SEDNA_BERT_Library.<br><br>
        An end-to-end BERT framework for training/testing is now fully activated.<br><br>
        BERT, RoBERTa, and DeBERTa are supported
    </div>
    """
    display(HTML(html_code))

_show_sedna_welcome()

'''
# ====================================================================================
# ====================================================================================
