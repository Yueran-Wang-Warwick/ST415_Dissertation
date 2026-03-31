import platform
import sys

# ====== Basic utilities for data handling and visualization ======
import collections
import tqdm
import matplotlib
import matplotlib.pyplot as plt
import plotly
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import label_binarize

# ====== Core deep learning libraries (PyTorch) ======
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

# ====== Hugging Face ecosystem: data and pretrained models ======
import datasets
from datasets import load_dataset
import transformers
from transformers import AutoTokenizer






#  =============================================================================================

### 2. Apply_Tokenization()
def Apply_Tokenization(training_set=None, testing_set=None, tokenizer=None):
    """
    Applies tokenization to a Hugging Face Dataset and generates an 'ids' field.

    Parameters:
        training_set: Hugging Face Dataset object (training set), must contain a 'text' field.
        testing_set: Hugging Face Dataset object (testing set, optional), must contain a 'text' field.
        tokenizer: Model name string or a pre-loaded tokenizer object.

    Returns:
        If only training_set is provided: Returns (training_set_tokenized, tokenizer).
        If both training_set and testing_set are provided: Returns (training_set_tokenized, testing_set_tokenized, tokenizer).
    """

    # 0. Safety check: Prevent crash if tokenizer is None.
    if tokenizer is None:
        raise ValueError("❌ Please pass tokenizer name or tokenizer object.")

    # 1. If a model name string is passed -> Automatically load the tokenizer.
    if isinstance(tokenizer, str):
        tokenizer = AutoTokenizer.from_pretrained(tokenizer)

    # 2. Complete pad_token (required for subsequent DataLoader).
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 3. Internal function to map 'text' -> 'ids'.
    def tokenize_function(example):
        return {
            "ids": tokenizer(
                example["text"],
                truncation=True,  # Truncate texts longer than max_length.
                max_length=512,  # Set the maximum sequence length to 512.
                padding=False  # Do not apply batch padding here; defer to DataLoader.
            )["input_ids"]
        }

    # 4. Apply tokenization to the training_set.
    if training_set is not None:
        training_set = training_set.map(tokenize_function, batched=True)
        print(f"✅ Training set tokenized. New features: {training_set.features.keys()}")

    # 5. Apply tokenization to the testing_set (if provided).
    if testing_set is not None:
        testing_set = testing_set.map(tokenize_function, batched=True)
        print(f"✅ Testing set tokenized. New features: {testing_set.features.keys()}")

    # 6. Register the tokenizer as a global variable for use in get_data_loader.
    current_module = sys.modules[__name__]
    current_module.tokenizer = tokenizer

    # Mount the raw datasets globally for Misclassification() to retrieve Text.
    current_module.raw_training_set = training_set
    current_module.raw_testing_set = testing_set

    # 7. Return datasets based on the input quantity.
    if testing_set is None:
        return training_set, tokenizer
    else:
        return training_set, testing_set, tokenizer
# =============================================================================================

### 3. get_data_loader()
def get_data_loader(dataset, batch_size, shuffle=True):
    """
    Combine batch processing and DataLoader creation into a single function.
    Parameters remain exactly the same:
        - dataset: The input PyTorch/Hugging Face Dataset object.
        - batch_size: The number of samples per batch.
        - shuffle: Whether to randomly shuffle the data (default is True).
    Everything else (logic, comments, behavior) stays unchanged.
    """

    # ======== Define pad_index from tokenizer (use global tokenizer) ========
    try:
        # Retrieve the padding token ID from the globally defined tokenizer.
        pad_index = tokenizer.pad_token_id
    except NameError:
        raise NameError("❌ 'tokenizer' is not defined. Please ensure Apply_Tokenization() has been called and returned a tokenizer.")

    # ======== Collate (Batch Process) Function Definition (Previously get_batch_process) ========
    def batch_process(batch):
        # Extract token IDs from the batch and apply dynamic padding.
        batch_ids = [i["ids"] for i in batch]
        batch_ids = nn.utils.rnn.pad_sequence(
            # Pads the sequences to the length of the longest sequence in the batch.
            batch_ids, padding_value=pad_index, batch_first=True
        )

        # Extract the labels and stack them into a single tensor.
        batch_label = [i["label"] for i in batch]
        batch_label = torch.stack(batch_label)

        # Create an Attention Mask: 1 for actual tokens, 0 for padding tokens.
        attention_mask = (batch_ids != pad_index).long()

        # Pack the processed Tensors into the final batch dictionary.
        batch = {"ids": batch_ids, "label": batch_label, "attention_mask": attention_mask}
        return batch

    # ======== Create DataLoader (Same as Before) ========
    data_loader = torch.utils.data.DataLoader(
        # The DataLoader iterates over this dataset and extracts one batch of samples at a time.
        dataset=dataset,
        batch_size=batch_size,

        # Use the custom function "batch_process()" (collate_fn) to combine individual rows into one padded batch.
        collate_fn=batch_process,

        # Randomise the order of samples in the dataset each epoch.
        shuffle=shuffle,
    )
    return data_loader
# =============================================================================================

### 4. Train_Validate_Test_Loader()
def Train_Validate_Test_Loader(training_set=None, testing_set=None, validation_size=None, batch_size=8):
    """
    Splits the original dataset into training and validation sets, converts them to PyTorch format,
    and returns the corresponding DataLoaders.

    Parameters:
        training_set: Hugging Face Dataset object, must contain 'ids' and 'label' fields.
        testing_set: Hugging Face Dataset object (optional), must contain 'ids' and 'label' fields.
        validation_size: Proportion of the training set to use as the validation set (default 0.25).
        batch_size: Batch size for the DataLoaders (default 8).
    """
    # Split the data based on the specified validation_size (e.g., 25% for validation).
    train_valid_data = training_set.train_test_split(test_size=validation_size)

    # Assign the resulting splits to meaningful variable names.
    train_data = train_valid_data["train"]
    valid_data = train_valid_data["test"]

    # Convert the datasets to the "torch" format.
    train_data = train_data.with_format(type="torch", columns=["ids", "label"])
    valid_data = valid_data.with_format(type="torch", columns=["ids", "label"])

    # Create DataLoader for the Training set.
    train_data_loader = get_data_loader(
        dataset=train_data,
        batch_size=batch_size)

    # Create DataLoader for the Validation set.
    valid_data_loader = get_data_loader(
        dataset=valid_data,
        batch_size=batch_size)

    # Create DataLoader for the Testing set (if testing_set is provided).
    test_data_loader = None
    if testing_set is not None:

        # Convert testing set to PyTorch format.
        testing_set = testing_set.with_format(type="torch", columns=["ids", "label"])
        test_data_loader = get_data_loader(
            dataset=testing_set,
            batch_size=batch_size)

    # NEW: Register DataLoaders as global variables for direct use in Training_loop() and other functions.
    current_module = sys.modules[__name__]
    current_module.train_data_loader = train_data_loader
    current_module.valid_data_loader = valid_data_loader
    current_module.test_data_loader = test_data_loader

    return train_data_loader, valid_data_loader, test_data_loader
# =============================================================================================

### 5. Sentiment_Analysis()
class Sentiment_Analysis(nn.Module):

    def __init__(self, selected_transformer=None, category_num=3, freeze_base_model_param=False):
        super().__init__()

        # If a model name string is passed, automatically load the model.
        # If selected_transformer=None, no model is loaded (user must explicitly provide one later).
        if isinstance(selected_transformer, str):
            self.selected_transformer = transformers.AutoModel.from_pretrained(selected_transformer)
        else:
            self.selected_transformer = selected_transformer

        # Get the hidden dimension from the transformer configuration (e.g., BERT-base uses 768).
        hidden_dim = self.selected_transformer.config.hidden_size

        # Define the classification head (a fully connected linear layer)
        # This layer maps the final hidden state vector (hidden_dim) to the number of output classes (category_num).
        # The weight matrix W has shape (768 × category_num) and bias b has shape (1 × category_num).
        self.fc = nn.Linear(hidden_dim, category_num)

        # Optional: Freeze the parameters of the base transformer model.
        if freeze_base_model_param:
            for param in self.selected_transformer.parameters():
                param.requires_grad = False

    # -------------------------------------------------------------------------

    def forward(self, ids, attention_mask=None):

        # Execute the forward pass through the pre-trained transformer model.
        output = self.selected_transformer(

            # Pass the token IDs and attention mask into the BERT model.
            input_ids=ids,
            attention_mask=attention_mask,

            # Exclude the attention matrix output to conserve computing power.
            output_attentions=False)

        # Retrieve the hidden states from the last encoder layer
        # Shape: last_hidden_state = [batch_size, seq_len, hidden_dim]
        hidden = output.last_hidden_state

        # Extract the hidden state corresponding to the [CLS] token (the first token, index 0).
        # Shape changes from [batch_size, seq_len, 768] to [batch_size, 768].
        cls_hidden = hidden[:, 0, :]

        # 1. Apply a tanh activation function to the [CLS] vectors, normalizing values to [-1, 1].
        # 2. Feed the activated vectors into the fully connected layer (self.fc).
        # This projects the contextualized [CLS] embedding to the raw classification Logits.
        # Output Logits shape: [batch_size, category_num].
        Logits = self.fc(torch.tanh(cls_hidden))

        # Overall process flow:
        # BERT_base → ids & attention_mask → 12 Encoder Iterations
        # → Extract Contextual [CLS] Embedding from last_hidden_state
        # → tanh Activation → Linear Projection (Fully Connected) → Logits Prediction
        return Logits
# =============================================================================================

### 6. X_Entropy_Hypersetting()
def X_Entropy_Hypersetting(Sentiment_Model, lr=1e-5, optimizer_selected="adamw", device=None):
    """
    Configures the essential components required for Cross-Entropy training (optimizer, loss function, device assignment).

    Parameters:
        Sentiment_Model: Your instantiated model object.
        lr: Learning rate (default is 1e-5).
        optimizer_selected: Type of optimizer to select: "adam" or "adamw" (default "adamw").
        device: Target device: "cpu" or "cuda". If None, it automatically detects the available device.

    Returns:
        optimizer, Loss_function, device
    """

    # 1. Select the Optimizer
    if optimizer_selected.lower() == "adam":
        optimizer = torch.optim.Adam(Sentiment_Model.parameters(), lr=lr)
    elif optimizer_selected.lower() == "adamw":

        # AdamW includes decoupled weight decay
        optimizer = torch.optim.AdamW(Sentiment_Model.parameters(), lr=lr, weight_decay=1e-4)
    else:
        raise ValueError("❌ optimizer_selected must be 'adam' or 'adamw'.")

    # 2. Define the Loss Function
    Loss_function = nn.CrossEntropyLoss()

    # 3. Device Selection
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(device)

    Sentiment_Model = Sentiment_Model.to(device)
    Loss_function = Loss_function.to(device)

    # Mount key training variables as global for direct access by Training_loop.
    current_module = sys.modules[__name__]
    current_module.Sentiment_Model = Sentiment_Model
    current_module.optimizer = optimizer
    current_module.Loss_function = Loss_function
    current_module.device = device

    return optimizer, Loss_function, device
#  =============================================================================================

### 7. iterative_train()
def iterative_train(data_loader, model, Loss_function, optimizer, device):
    # Switch the model to the "Training mode". This enables features like Dropout.
    model.train()

    # Initialize containers to store loss and accuracy for the current epoch.
    epoch_losses, epoch_accs = [], []

    # Iterate over the data loader, processing data in batches
    for batch in tqdm.tqdm(data_loader, desc="Training in progress..."):

        # 1. Data Loading: Transfer batch tensors to the specified device (GPU/CPU).
        ids = batch["ids"].to(device)
        label = batch["label"].to(device)
        attention_mask = batch["attention_mask"].to(device)

        # 2. Forward Pass: Input the data into the model's forward() function to get Logits.
        Logits = model(ids, attention_mask=attention_mask)

        # 3. Compute Metrics: Calculate the loss and accuracy using the Logits and true labels.
        loss = Loss_function(Logits, label)
        # Note: get_accuracy() function is defined elsewhere in the file
        accuracy = get_accuracy(Logits, label)

        # --- Optimization Steps ---

        # Step 1: Zero the gradients.
        # PyTorch accumulates gradients by default. This must be cleared at the start of every batch
        # to prevent the current batch's gradients from being influenced by previous updates.
        optimizer.zero_grad()

        # Step 2: Backpropagation.
        # Computes the gradient of the loss with respect to all trainable parameters.
        loss.backward()

        # Step 3: Update Parameters.
        # The optimizer reads the calculated gradients and updates the model's weights
        optimizer.step()

        # 4. Record Metrics: Append the batch loss and accuracy to the epoch containers.
        epoch_losses.append(loss.item())
        epoch_accs.append(accuracy.item())

        # 5. Compute and return the average loss and accuracy across all batches in the epoch.
    return np.mean(epoch_losses), np.mean(epoch_accs)
#  =============================================================================================

### 8. iterative_evaluate

def iterative_evaluate(data_loader, model, Loss_function, device):
    # Switch the model to the "Evaluation mode". This disables Dropout and batch normalization tracking.
    model.eval()

    # Initialize containers to store loss and accuracy for the evaluation epoch.
    epoch_losses, epoch_accs = [], []

    # Disable gradient computation as we only perform forward propagation and do not need to update weights.
    with torch.no_grad():
        for batch in tqdm.tqdm(data_loader, desc="Validating in progress..."):

            # 1. Data Loading
            ids = batch["ids"].to(device)
            label = batch["label"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            # 2. Forward Pass
            Logits = model(ids, attention_mask=attention_mask)

            # 3. Compute Metrics
            loss = Loss_function(Logits, label)
            accuracy = get_accuracy(Logits, label)

            # 4. Record Metrics
            epoch_losses.append(loss.item())
            epoch_accs.append(accuracy.item())

    # 5. Compute and return the average loss and accuracy across all batches.
    return np.mean(epoch_losses), np.mean(epoch_accs)

#  =============================================================================================

### 9. get_accuracy
def get_accuracy(Logits, label):
    # Determine the batch size from the shape of the Logits tensor.
    # Logits shape: [batch_size, output_dim]
    batch_size = Logits.shape[0]

    # Find the predicted class index by taking the index of the maximum value along the last dimension (output_dim).
    predicted_classes = Logits.argmax(dim=-1)

    # Compare predicted classes with true labels element-wise.
    correct_predictions = predicted_classes.eq(label).sum()

    # Calculate the batch accuracy
    accuracy = correct_predictions / batch_size
    return accuracy
# =============================================================================================

### 10. Training_loop
def Training_loop(
        epoch_num=None,
        save_dir=None,
        step_interval=1
):
    """
    Training loop for the sentiment analysis model.

    Adjustable Parameters:
        epoch_num: The total number of training epochs (default 3).
        save_dir: Path where the best model parameters (.pt file) will be saved.
        step_interval: Record training metrics every N steps for fine-grained visualization (default 1).
    """
    required_vars = [
        "train_data_loader",
        "valid_data_loader",
        "Sentiment_Model",
        "Loss_function",
        "optimizer",
        "device"
    ]
    for var in required_vars:
        if var not in globals():
            raise RuntimeError(
                f"❌ Missing global variable: {var}. "
                f"Please ensure Apply_Tokenization(), Train_Validate_Test_Loader(), "
                f"and X_Entropy_Hypersetting() are called before Training_loop()."
            )

    best_valid_loss = float("inf")
    best_model_state = None

    # Create a dictionary to store training and validation loss/accuracy for later visualisation.
    metrics = collections.defaultdict(list)

    # Initialize step-level metrics containers.
    metrics["step"] = []
    metrics["step_loss"] = []
    metrics["step_acc"] = []
    global_step = 0

    for epoch in range(epoch_num):
        Sentiment_Model.train()

        total_train_loss = []
        total_train_acc = []

        # Initialize tqdm progress bar, fixed at the bottom
        progress_bar = tqdm.tqdm(train_data_loader, desc=f"Epoch {epoch} / Training...")

        for batch in progress_bar:
            ids = batch["ids"].to(device)
            label = batch["label"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            logits = Sentiment_Model(ids, attention_mask=attention_mask)
            loss = Loss_function(logits, label)
            acc = get_accuracy(logits, label)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # Log step-level data according to step_interval.
            if global_step % step_interval == 0:
                metrics["step"].append(global_step)
                metrics["step_loss"].append(loss.item())
                metrics["step_acc"].append(acc.item())

            # Accumulate batch loss/acc to calculate the epoch average later.
            total_train_loss.append(loss.item())
            total_train_acc.append(acc.item())

            global_step += 1

        # Calculate epoch average based on accumulated batch loss/acc.
        train_loss = float(np.mean(total_train_loss))
        train_acc = float(np.mean(total_train_acc))

        # Run the validation set evaluation (keeping original logic).
        valid_loss, valid_acc = iterative_evaluate(
            valid_data_loader, Sentiment_Model, Loss_function, device)

        # Record epoch-level metrics.
        metrics["train_losses"].append(train_loss)
        metrics["train_accs"].append(train_acc)
        metrics["valid_losses"].append(valid_loss)
        metrics["valid_accs"].append(valid_acc)

        # Save the model state if the current validation loss is the best so far.
        if valid_loss < best_valid_loss:
            best_valid_loss = valid_loss
            best_model_state = Sentiment_Model.state_dict()

        # Print epoch summary.
        print(f"epoch: {epoch}")
        print(f"train_loss: {train_loss:.3f}, train_acc: {train_acc:.3f}")
        print(f"valid_loss: {valid_loss:.3f}, valid_acc: {valid_acc:.3f}")

    # Save the best model state if a save directory is provided.
    if best_model_state is not None and save_dir is not None:
        torch.save(best_model_state, save_dir)
        print(f"✅ Model saved to: {save_dir}")

    # Save the metrics dictionary to the global namespace
    current_module = sys.modules[__name__]
    current_module.metrics = metrics

    return metrics



# =============================================================================================

# 11. Visualisation()
def Visualisation(Model_Name=None):
    """
    Visualise the training process using the recorded metrics.

    No parameters are required, as it defaults to using the global 'metrics' variable stored
    by the Training_loop() function.
    If Model_Name is provided, it is prepended to all plot titles for easy comparison between models.
    Example:
        Visualisation(Model_Name="DeBERTa")
    """

    if "metrics" not in globals():
        raise RuntimeError("❌ 'metrics' not found. Please run Training_loop() first and ensure metrics is stored.")

    global metrics


    prefix = f"{Model_Name}: " if Model_Name else ""

    if "step" in metrics and len(metrics["step"]) > 0:
        plt.figure(figsize=(10, 5))
        step = np.asarray(metrics["step"])
        step_loss = np.asarray(metrics["step_loss"])
        step_acc = np.asarray(metrics["step_acc"])

        def _bin_series(x, y, max_bins=400):
            if len(x) <= max_bins:
                return x, y
            # Divide data into max_bins equal-sized bins and calculate the mean within each bin.
            edges = np.linspace(0, len(x), max_bins + 1, dtype=int)
            bx, by = [], []
            for i in range(max_bins):
                s, e = edges[i], edges[i + 1]
                bx.append(x[s:e].mean())
                by.append(y[s:e].mean())
            return np.asarray(bx), np.asarray(by)

        bx_loss, by_loss = _bin_series(step, step_loss, max_bins=400)
        bx_acc, by_acc = _bin_series(step, step_acc, max_bins=400)

        # Loss Curve
        plt.subplot(1, 2, 1)
        plt.plot(bx_loss, by_loss, linewidth=1.2, color="#a9061b")
        plt.title(prefix + "Training Loss over Steps")
        plt.xlabel("Steps")
        plt.ylabel("Loss")
        plt.grid(alpha=0.3)

        # Accuracy Curve
        plt.subplot(1, 2, 2)
        plt.plot(bx_acc, by_acc, linewidth=1.2, color="#195db7")
        plt.title(prefix + "Training Accuracy over Steps")
        plt.xlabel("Steps")
        plt.ylabel("Accuracy")
        plt.grid(alpha=0.3)

        plt.tight_layout()
        plt.show()

    # If the number of epochs is 1 or less, skip drawing the Epoch-level curves.
    if "train_losses" not in metrics or len(metrics["train_losses"]) <= 1:
        return

    # ========== Epoch-Level Curves: Overall Trend Analysis ==========
    plt.figure(figsize=(10, 5))

    # Left Plot: Loss - Train vs Valid
    plt.subplot(1, 2, 1)
    plt.plot(metrics["train_losses"], linewidth=1.5, color="#a9061b", label="Train Loss")
    plt.plot(metrics["valid_losses"], linewidth=1.5, color="#195db7", label="Valid Loss")
    plt.title(prefix + "Loss over Epochs")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.grid(alpha=0.3)

    # Right Plot: Accuracy - Train vs Valid
    plt.subplot(1, 2, 2)
    plt.plot(metrics["train_accs"], linewidth=1.5, color="#a9061b", label="Train Acc")
    plt.plot(metrics["valid_accs"], linewidth=1.5, color="#195db7", label="Valid Acc")
    plt.title(prefix + "Accuracy over Epochs")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.grid(alpha=0.3)

    plt.tight_layout()
    plt.show()


# =============================================================================================
def Test_model(Model=None, Label_mapping=None):
    """
    Optimized function to evaluate model performance on the test set (fully self-contained).

    This function performs a single forward pass over the test data, computes all relevant
    metrics (Loss, Accuracy, Precision, Recall, F1, Confusion Matrix), utilizes GPU acceleration,
    and automatically logs misclassified samples along with their confidence scores.

    Parameters:
        Model: The loaded PyTorch model instance to be evaluated.
        Label_mapping: Dictionary mapping numerical labels to readable names (e.g., {0: "Negative"}).

    Returns:
        df_result (pandas.DataFrame): A table containing class-wise and weighted total metrics.
    """

    # Global Variable Check
    required_vars = ["test_data_loader", "Loss_function", "device"]
    for var in required_vars:
        if var not in globals():
            raise RuntimeError(
                f"Missing global variable: {var}. "
                "Please ensure Train_Validate_Test_Loader() and X_Entropy_Hypersetting() "
                "have been called before Test_model()."
            )

    device = globals()["device"]
    Loss_function = globals()["Loss_function"]

    # Initialize Containers
    all_logits, all_preds, all_labels = [], [], []
    epoch_losses, epoch_accs = [], []

    # Forward Pass: Single Inference
    Model.eval()
    with torch.no_grad():
        for batch in tqdm(
                test_data_loader,
                desc="Validating in progress...",
                ncols=100,
                dynamic_ncols=True,
                leave=True,
                file=sys.stdout,
                mininterval=0.2
        ):
            ids = batch["ids"].to(device)
            labels = batch["label"].to(device)
            mask = batch["attention_mask"].to(device)

            # --- Forward pass ---
            logits = Model(ids, attention_mask=mask)

            # --- Compute loss & accuracy ---
            loss = Loss_function(logits, labels)
            preds = torch.argmax(logits, dim=1)
            acc = (preds == labels).float().mean()

            # --- Record and detach tensors ---
            epoch_losses.append(loss.item())
            epoch_accs.append(acc.item())

            all_logits.append(logits.detach().cpu())
            all_preds.append(preds.detach().cpu())
            all_labels.append(labels.detach().cpu())

    # Consolidate Results
    all_logits = torch.cat(all_logits)
    all_preds = torch.cat(all_preds)
    all_labels = torch.cat(all_labels)

    test_loss = float(np.mean(epoch_losses))
    test_acc = float(np.mean(epoch_accs))

    # Calculate Precision, Recall, and F1 using 'weighted' averaging.
    precision = precision_score(all_labels, all_preds, average="weighted", zero_division=0)
    recall = recall_score(all_labels, all_preds, average="weighted", zero_division=0)
    weighted_F1 = f1_score(all_labels, all_preds, average="weighted", zero_division=0)

    # Compute the Confusion Matrix.
    conf_matrix = confusion_matrix(all_labels, all_preds)

    # Calculate Class-wise Metrics
    unique_classes = sorted(set(all_labels.numpy()))
    records = []

    for c in unique_classes:
        idx = (all_labels == c)
        cls_labels = all_labels[idx]
        cls_preds = all_preds[idx]
        cls_logits = all_logits[idx]

        # Calculate Accuracy for the current class
        cls_acc = (cls_labels == cls_preds).float().mean().item() if len(cls_labels) > 0 else 0.0

        # Calculate Loss for the current class
        if len(cls_labels) > 0:
            with torch.no_grad():
                cls_logits_gpu = cls_logits.to(device)
                cls_labels_gpu = cls_labels.to(device)

                # Use Cross-Entropy Loss function for class-wise loss calculation.
                cls_loss = F.cross_entropy(cls_logits_gpu, cls_labels_gpu, reduction='mean').item()
        else:
            cls_loss = 0.0

        # Retrieve Class-wise Precision / Recall / F1.
        precision_c = precision_score(all_labels, all_preds, average=None, zero_division=0)[c]
        recall_c = recall_score(all_labels, all_preds, average=None, zero_division=0)[c]
        f1_c = f1_score(all_labels, all_preds, average=None, zero_division=0)[c]

        label_name = Label_mapping.get(c, str(c)) if Label_mapping else str(c)
        records.append({
            "Label": label_name,
            "Test_Loss": round(cls_loss, 3),
            "Test_Acc": round(cls_acc, 3),
            "Precision": round(precision_c, 3),
            "Recall": round(recall_c, 3),
            "F1": round(f1_c, 3)
        })

    # --- Weighted Total Summary ---
    records.append({
        "Label": "Weighted_Total",
        "Test_Loss": round(test_loss, 3),
        "Test_Acc": round(test_acc, 3),
        "Precision": round(precision, 3),
        "Recall": round(recall, 3),
        "F1": round(weighted_F1, 3)
    })

    df_result = pd.DataFrame(records)


    # Misclassified Sample Collection
    misclassified = []

    # Identify indices where true label does not equal predicted label.
    mis_idx = torch.where(all_labels != all_preds)[0]
    if len(mis_idx) > 0:
        with torch.no_grad():

            # Calculate confidence for the predicted (incorrect) class.
            logits_sub = all_logits[mis_idx].to(device)
            preds_sub = all_preds[mis_idx].to(device)
            probs_sub = torch.softmax(logits_sub, dim=-1)

            # Gather probability of the predicted class using predicted indices.
            confs = probs_sub.gather(1, preds_sub.unsqueeze(1)).squeeze(1).cpu()

        for j, i in enumerate(mis_idx):
            misclassified.append({
                "text_index": int(i.item()),
                "true_label": int(all_labels[i]),
                "predicted_label": int(all_preds[i]),
                "confidence": round(confs[j].item(), 3)
            })

    # Register Global Variables
    current_module = sys.modules[__name__]
    current_module.test_confusion_matrix = conf_matrix
    current_module.test_roc_data = {"labels": all_labels.numpy(), "logits": all_logits.numpy()}
    current_module.test_misclassified_samples = misclassified
    current_module.test_metrics = {
        "test_loss": test_loss,
        "test_acc": test_acc,
        "precision": precision,
        "recall": recall,
        "weighted_F1": weighted_F1
    }
    return df_result


# =============================================================================================

# 13. Confusion_matrix_ROC()
def Confusion_matrix_ROC(Model_Name=None):
    """
    Utilizes global data saved by Test_model() to generate two plots in one go:
        1. Confusion Matrix
        2. Multi-class ROC Curve (One-vs-Rest strategy)
    The function uses a low-saturation, minimalist color scheme (inspired by Apple design)
    and allows for a model name prefix to be added to titles.
    Example:
        Confusion_matrix_ROC(Model_Name="DeBERTa")
    """

    # ===== Dependency Data Check =====
    required_vars = ["test_confusion_matrix", "test_roc_data"]
    for var in required_vars:
        if var not in globals():
            raise RuntimeError(
                f"Missing global variable: '{var}'. "
                "Please run Test_model() before calling Confusion_matrix_ROC()."
            )

    cm = test_confusion_matrix
    labels = test_roc_data["labels"]
    logits = test_roc_data["logits"]

    num_classes = logits.shape[1]

    # Convert logits to probabilities using Softmax
    probs = torch.softmax(torch.tensor(logits), dim=1).numpy()

    # Binarize the true labels for the One-vs-Rest calculation
    labels_binarized = label_binarize(labels, classes=np.arange(num_classes))

    # Prepend model name to original title
    prefix = f"{Model_Name}: " if Model_Name else ""

    # Color Scheme
    cm_cmap = sns.light_palette("#7BA18F", as_cmap=True)
    roc_colors = [
        "#4F6D7A",
        "#A06B9A",
        "#6A8E7F",
        "#B97A57",
        "#6D597A",
        "#8E9AAF",
        "#9A8F97",
        "#718CA1",
        "#8FBC94",
        "#C1A192",
    ][:num_classes]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    plt.style.use("default")

    # Confusion Matrix
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap=cm_cmap,
        cbar=False,
        linewidths=0.5,
        linecolor="#ECECEC",
        ax=axes[0],
        annot_kws={"size": 11, "weight": "bold", "color": "#2E2E2E"}
    )
    axes[0].set_title(prefix + "Confusion Matrix", fontsize=13, fontweight="bold", color="#2E2E2E")
    axes[0].set_xlabel("Predicted Label", fontsize=11, color="#2E2E2E")
    axes[0].set_ylabel("True Label", fontsize=11, color="#2E2E2E")
    axes[0].tick_params(axis='both', colors='#4A4A4A')

    # ROC Curve
    for i in range(num_classes):
        # Calculate False Positive Rate (fpr) and True Positive Rate (tpr) for each class
        fpr, tpr, _ = roc_curve(labels_binarized[:, i], probs[:, i])
        axes[1].plot(fpr, tpr, lw=1.5, color=roc_colors[i], label=f"Class {i}")

    axes[1].plot([0, 1], [0, 1], "k--", lw=1, alpha=0.5)
    axes[1].set_title(prefix + "ROC Curve (One-vs-Rest)", fontsize=13, fontweight="bold", color="#2E2E2E")
    axes[1].set_xlabel("False Positive Rate", fontsize=11, color="#2E2E2E")
    axes[1].set_ylabel("True Positive Rate", fontsize=11, color="#2E2E2E")
    axes[1].tick_params(axis='both', colors='#4A4A4A')
    axes[1].grid(alpha=0.2)
    axes[1].legend(frameon=False, fontsize=9, loc="lower right")

    plt.tight_layout()
    plt.show()

# =============================================================================================

# 14. Misclassification()
def Misclassification(Label_mapping=None):
    """
    Returns a DataFrame of the model's misclassified samples (up to 50 samples), including:
        1. Index (starting from 1)
        2. True_label
        3. Model_label (The class predicted by the model)
        4. Confidence (The model's probability score for the predicted incorrect class)
        5. Text (The original text content)

    Optional Parameter:
        Label_mapping: A dictionary, e.g., {0: "Negative", 1: "Positive", 2: "Gibberish"},
                       to replace numerical labels with human-readable class names.

    Dependencies (Global variables stored by Test_model() and Apply_Tokenization()):
        - test_misclassified_samples
        - raw_testing_set
    """

    # Dependency Check
    if "test_misclassified_samples" not in globals():
        raise RuntimeError("'test_misclassified_samples' not found. Please run Test_model() first.")

    if len(test_misclassified_samples) == 0:
        print("No misclassified samples found. Model classified everything correctly.")
        return pd.DataFrame()

    # Build DataFrame
    records = []
    for i, sample in enumerate(test_misclassified_samples):
        records.append({
            "Index": i + 1,
            "True_label": sample["true_label"],
            "Model_label": sample["predicted_label"],
            "Confidence": sample.get("confidence", None),
            "Text_index": sample["text_index"]
        })

    df = pd.DataFrame(records)

    # Apply Label Mapping
    if Label_mapping is not None and isinstance(Label_mapping, dict):
        # Replace numerical labels with names using the mapping dictionary.
        df["True_label"] = df["True_label"].map(Label_mapping).fillna(df["True_label"])
        df["Model_label"] = df["Model_label"].map(Label_mapping).fillna(df["Model_label"])

    # Retrieve Original Text
    texts = []
    for row in df["Text_index"]:
        try:
            if "raw_testing_set" in globals() and row < len(raw_testing_set):
                # Access the original text using the index saved during tokenization.
                texts.append(raw_testing_set[row]["text"])
            else:
                texts.append("(Text not found)")
        except Exception:
            texts.append("(Failed to recover text)")

    df["Text"] = texts

    # Drop the temporary index column used for retrieval
    df = df.drop(columns=["Text_index"])

    return df

# =============================================================================================

### 15. Reload_Model()

def Reload_Model(base_model=None, model_dir=None, device_selected="cuda"):
    """
    Reloads the trained model parameters and returns a model object ready for inference/testing.

    Parameters:
        base_model: The name of the base model (must match the model used during training, e.g., "bert-base-uncased").
        model_dir: The file path to the saved model parameters (.pt file).
        device_selected: The target device: 'cuda' or 'cpu' (default 'cuda').

    Returns:
        The model object with loaded parameters, placed on the specified device.
    """
    # Parameter validation
    if base_model is None or model_dir is None:
        raise ValueError("Please explicitly pass base_model='...' and model_dir='...pt'")

    tokenizer = AutoTokenizer.from_pretrained(base_model)

    if isinstance(tokenizer, str):
        tokenizer = AutoTokenizer.from_pretrained(base_model)

    # 2. Complete pad_token (required for subsequent DataLoader).
    if tokenizer.pad_token is None:
        if tokenizer.eos_token is not None:
            tokenizer.pad_token = tokenizer.eos_token
        elif tokenizer.sep_token is not None:
            tokenizer.pad_token = tokenizer.sep_token
        else:
            tokenizer.pad_token = tokenizer.unk_token

    current_module = sys.modules[__name__]
    current_module.tokenizer = tokenizer
    # Device selection
    device = torch.device(device_selected)

    # 1. Reconstruct the model architecture
    Reload_BERT = Sentiment_Analysis(
        selected_transformer = base_model,   # Ensure the base model is consistent with training
        category_num = 3,
        freeze_base_model_param = False
    ).to(device)

    # 2. Load the saved state dictionary
    state_dict = torch.load(model_dir, map_location=device)
    # Apply the loaded state dictionary to the new model instance
    Reload_BERT.load_state_dict(state_dict)

    device = torch.device(device_selected)
    current_module = sys.modules[__name__]
    current_module.device = device

    print("Reloaded model: Reload_BERT has been loaded")

    return Reload_BERT

# =============================================================================================
# 15. Sentiment_Classification()
def Sentiment_Classification(text, BERT_Model=None, Label_mapping=None, max_length=256):
    """
    Performs sentiment classification inference on a single piece of text OR a batch of texts.

    Parameters:
        text: A single text string OR a list/tuple of text strings.
        BERT_Model: The loaded model object (default None; must be obtained via Reload_Model() beforehand).
        Label_mapping: Dictionary for label mapping, e.g., {0: "Negative", 1: "Positive", 2: "Gibberish"}.
                       If None, the function retains the numerical label.
        max_length: Max token length for truncation (default 256). Only used in the batch-capable tokenizer path.

    Dependencies (Global variables mounted by X_Entropy_Hypersetting / Apply_Tokenization):
        - tokenizer
        - device

    Output:
        Prints the predicted label and confidence.
        Returns:
          - If input is a single string: (pred_label, confidence)
          - If input is a list/tuple:   [(pred_label, confidence), ...]
    """

    # ===== Dependency Check =====
    if BERT_Model is None:
        raise ValueError("Please pass a loaded model into Sentiment_Analysis(BERT_Model=...).")
    if "tokenizer" not in globals():
        raise RuntimeError("'tokenizer' not found. Please call Apply_Tokenization() first.")
    if "device" not in globals():
        raise RuntimeError("'device' not found. Please run X_Entropy_Hypersetting() first.")

    # ===== Normalise input to a batch =====
    single_input = isinstance(text, str)
    if single_input:
        texts = [text]
    else:
        if not isinstance(text, (list, tuple)):
            raise TypeError("text must be a str, list[str], or tuple[str].")
        texts = list(text)
        if len(texts) == 0:
            return []
        for t in texts:
            if not isinstance(t, str):
                raise TypeError("All elements in text batch must be strings.")

    # ===== Tokenize (batch-capable) =====
    enc = tokenizer(
        texts,
        padding=True,
        truncation=True,
        max_length=max_length,
        return_tensors="pt"
    )

    input_ids = enc["input_ids"].to(device)
    attention_mask = enc.get("attention_mask", None)
    if attention_mask is not None:
        attention_mask = attention_mask.to(device)

    # ===== Model Prediction =====
    BERT_Model.eval()
    with torch.no_grad():
        try:
            out = BERT_Model(input_ids, attention_mask=attention_mask) if attention_mask is not None else BERT_Model(input_ids)
        except TypeError:
            out = BERT_Model(input_ids)

        if hasattr(out, "logits"):
            logits = out.logits
        elif isinstance(out, (tuple, list)):
            logits = out[0]
        else:
            logits = out

    if logits.dim() == 1:
        logits = logits.unsqueeze(0)

    # ===== Softmax Probabilities & Predicted Result =====
    probs = torch.softmax(logits, dim=-1)
    pred_idxs = probs.argmax(dim=-1).tolist()
    confs = probs.max(dim=-1).values.tolist()

    # ===== Format outputs =====
    results = []
    for pred_idx, conf in zip(pred_idxs, confs):
        confidence = round(float(conf), 3)

        if Label_mapping is not None and isinstance(Label_mapping, dict):
            pred_label = Label_mapping.get(int(pred_idx), int(pred_idx))
        else:
            pred_label = int(pred_idx)

        print(f"Final Prediction: {pred_label}  |  Confidence = {confidence:.3f}")
        results.append((pred_label, confidence))

    return results[0] if single_input else results

# =============================================================================================
