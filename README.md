# MultiTaskSegNet

## Further Work - 
* Currently we are using W^tW to get the relative importance of information streams both for classification and reconstruction of image. Another possibility of getting this information is to use attention on the concatenated latent space representation of the information streams, since the magnitude of the multiplicative factor will tell us which features are more important. 

* In order to regularize/control the flow of information, we are planning to penalize the norm of W in the loss function. Integrating the idea with attention, we can introduce a ranking loss on the attention factors which penalizes a high difference between the (sum total of the attention given to each stream) with other streams, i.e. it emphasizes the need to have attention multipliers close to each other.

* Another idea for regularization is to tie weights in the first layer after the latent space vector representation for the reconstruction and classification tasks, since this means that the information flowing to the reconstruction task is the same as the info flowing to the classification task, further this could be done with a multiplicative factor.
