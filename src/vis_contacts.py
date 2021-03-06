from collections import OrderedDict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from bert_fold.dataset import ProteinNetDataset, prepare_targets
from bert_fold.modules.bert_fold import BertFold
from const import DATA_PROTEIN_NET_DIR


def load_model() -> BertFold:
    model = BertFold(pretrained=False)
    # Update here for your trained weight.
    ckpt = torch.load('../experiments/protein_supervised/1599530879/checkpoints/last.ckpt')

    if any(k.startswith('ema_model') for k in ckpt['state_dict'].keys()):
        prefix = 'ema_model'
    else:
        prefix = 'model'

    new_dict = OrderedDict()
    for k, v in ckpt['state_dict'].items():
        if not k.startswith(f'{prefix}.'):
            continue
        new_dict[k[len(f'{prefix}.'):]] = v

    info = model.load_state_dict(new_dict, strict=False)

    print(info)

    return model


# %%
if __name__ == '__main__':
    # %%
    df = pd.read_parquet(DATA_PROTEIN_NET_DIR / 'casp12/validation.pqt')
    dataset = ProteinNetDataset(df)

    # %%
    model = load_model().eval().cpu()

    # %%
    data = dataset[np.random.randint(len(dataset))]
    batch = ProteinNetDataset.collate([data])
    targets = prepare_targets(batch)

    pdb_id = data[-1]
    print(pdb_id[3:7])

    with torch.no_grad():
        out = model.forward(batch['input_ids'], batch['attention_mask'], targets)

    # %%
    seq_len = len(data[0]) - 2
    _, idx_i, idx_j = targets.dist.indices
    y_true = targets.dist.values.numpy()
    y_hat = out.y_hat[0][0].numpy()

    mat_true = np.full((seq_len, seq_len), np.nan)
    mat_true[idx_i, idx_j] = y_true
    mat_true[idx_j, idx_i] = y_true

    mat_pred = y_hat

    fig, axes = plt.subplots(nrows=1, ncols=2)
    fig.suptitle(f'Pairwise distance prediction: PDB {pdb_id}')
    axes[0].matshow(mat_true)
    axes[0].set_title('Ground Truth')
    axes[1].matshow(mat_pred)
    axes[1].set_title('Prediction')
    plt.show()

    print(out.mae_l_8)
