from tensorflow.keras.layers import Layer
import tensorflow as tf 

#MAY HAVE TO REWRITE STUFF FOR TF2 COMPAT
class MaxPool2D(Layer):

    def __init__(
            self,
            ksize=(2, 2),
            strides=(2, 2),
            padding='same',
            **kwargs):
        super(MaxPool2D, self).__init__(autocast=False)
        self.padding = padding
        self.pool_size = ksize
        self.strides = strides

    def call(self, inputs, **kwargs):
        padding = self.padding
        pool_size = self.pool_size
        strides = self.strides
        ksize = [1, pool_size[0], pool_size[1], 1]
        padding = padding.upper()
        strides = [1, strides[0], strides[1], 1]
        output, argmax = tf.nn.max_pool_with_argmax(
                inputs,
                ksize=ksize,
                strides=strides,
                padding=padding)
        argmax = tf.cast(argmax, tf.float64)
        return [output, argmax]

    def compute_output_shape(self, input_shape):
        ratio = (1, 2, 2, 1)
        output_shape = [
                dim//ratio[idx]
                if dim is not None else None
                for idx, dim in enumerate(input_shape)]
        output_shape = tuple(output_shape)
        return [output_shape, output_shape]

    def compute_mask(self, inputs, mask=None):
        return 2 * [None]


class MaxUnpool2D(Layer):
    def __init__(self, ksize=(2, 2), **kwargs):
        super(MaxUnpool2D, self).__init__(autocast=False,**kwargs)
        self.size = ksize

    def call(self, inputs, output_shape=None):
        updates, mask = inputs[0], inputs[1]
        mask = tf.cast(mask, 'int32')
        input_shape = tf.shape(updates, out_type='int32')
        #  calculation new shape
        if output_shape is None:
            output_shape = (
                    input_shape[0],
                    input_shape[1]*self.size[0],
                    input_shape[2]*self.size[1],
                    input_shape[3])
        self.output_shape1 = output_shape

        # calculation indices for batch, height, width and feature maps
        one_like_mask = tf.ones_like(mask, dtype='int32')
        batch_shape = tf.concat(
                [[input_shape[0]], [1], [1], [1]],
                axis=0)
        batch_range = tf.reshape(
                tf.range(output_shape[0], dtype='int32'),
                shape=batch_shape)
        # print("SHAPE______",output_shape[3])
        b = one_like_mask * batch_range
        y = mask // (output_shape[2] * output_shape[3])
        x = (mask // output_shape[3]) % output_shape[2]
        feature_range = tf.range(output_shape[3], dtype='int32')
        f = one_like_mask * feature_range

        # transpose indices & reshape update values to one dimension
        updates_size = tf.size(updates)
        indices = tf.transpose(tf.reshape(
            tf.stack([b, y, x, f]),
            [4, updates_size]))
        values = tf.reshape(updates, [updates_size])
        ret = tf.scatter_nd(indices, values, output_shape)
        return ret

    def compute_output_shape(self, input_shape):
        mask_shape = input_shape[1]
        return (
                mask_shape[0],
                mask_shape[1]*self.size[0],
                mask_shape[2]*self.size[1],
                mask_shape[3]
                )


class SelfAttention(Layer):
    '''
    The self attention layer here is mainly for regularization
    '''
    def __init__(self,layers):
        super(SelfAttention, self).__init__(autocast=False)
        self.model = tf.keras.Sequential(layers)

    @tf.function
    def call(self,X):
        attention_map = self.model(X)
        return X*attention_map #,tf.math.reduce_mean(attention_map)

    def get_attention_map(self,X):
        return self.model(X)

class CompleteAttention(Layer):
    '''
    Contrary to self attention, this looks at all streams and normalizes means
    '''
    def __init__(self,layers,num_streams):
        super(CompleteAttention, self).__init__(autocast=False)
        self.model = tf.keras.Sequential(layers)
        self.num_streams = num_streams

    def call(self,X):

        attention_map,means,meansum = self.get_attention_map(X)

        return X*attention_map,means,meansum

    @tf.function
    def get_attention_map(self,X):
        attention_map = self.model(X)   
        b,h,w,c       = attention_map.shape
        means         = []
        for i in range(self.num_streams):
            means.append(tf.math.reduce_mean(attention_map[:,:,:,i*(c//self.num_streams):(i+1)*(c//self.num_streams)]))
        
        meansum = 0
        for i in range(self.num_streams):
            meansum += means[i]

        # for i in range(self.num_streams):
        #   attention_map[:,:,:,i*(c//self.num_streams):(i+1)*(c//self.num_streams)] /= (meansum+1e-9)
        return attention_map,means,meansum
class ReshapeAndConcat(Layer):
    '''
    Reshapes and concats two inputs
    Needed for the discriminator
    '''
    def __init__(self):
        super(ReshapeAndConcat, self).__init__(autocast=False)

    def call(self,inputs):
        X_inp,X_gen = inputs
        bs,h,w,c = X_gen.shape
        x1,x2,x3,x4 = X_inp.shape
        #TODO ensure that shapes are compatible
        #This is a very bad fix, atleast
        # print(X_gen.dtype,X_inp.dtype)
        X = tf.concat([tf.reshape(X_inp,(bs,h,w,(x2*x3*x4)//(h*w))),tf.cast(X_gen,tf.float32)],axis=-1)
        return X
