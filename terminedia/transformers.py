from inspect import signature

from terminedia.utils import V2, Spatial, HookList


class Transformer:

    channels = "char foreground background effects".split()

    def __init__(self, char=None, foreground=None, background=None, effects=None, spatial=None, source=None, mode="normal"):
        """
        Each slot can be None, a static value, or a callable.

        Each of these callables can have in the signature named parameters with any combination of

            "self, value, char, foreground, background, effects, pixel, pos, source, context, tick"
            Each of these named parameters will be injected as an argument when the
            function is called.
                - "self": Transformer instance (it is, as the others, optional)
                - "value": the current value for this channel
                - "char, foreground, background, effects": the content of the respective channel
                - "pos": the pixel position,
                - "pixel" meaning the source pixel as transformed to this point on the pipeline ,
                - "source" meaning
                    the whole source shape. The callable should be careful to read the shape
                    with "get_raw", and not using __getitem__ to avoid an infinite loop
                    (an evolution of this may give a 'transformed down to here' view
                    of the shape, or a 3x3 and 5x5 kernel options)
                - "tick" meaning the "frame number" from app start, and in the future
                    will be used for animations. It is currently injected as "0".

        It should return the value to be used downstream of the named channel.

        """
        self.char = char
        self.foreground = foreground
        self.background = background
        self.effects = effects
        self.spatial = spatial
        self.source = source
        self.mode = mode

        self.signatures = {
            channel: frozenset(signature(getattr(self, channel)).parameters.keys()) if getattr(self, channel) else () for channel in self.channels
        }


    def __repr__(self):
        return "Transformer <{}{}>".format(
            ", ".join(channel for channel in self.channels if getattr(self, channel + "_f", None)),
            f", source={self.source!r},  mode={self.mode!r}" if self.source else "",
        )


class TransformersContainer(HookList):
    def __init__(self, *args):
        super().__init__(*args)
        self.stack = self.data

    def insert_hook(self, item):
        item = super().insert_hook(item)
        if not isinstance(item, Transformer):
            raise TypeError("Only Transformer instances can be added to a TransformersContainer")
        item.container = self
        return item

    def process(self, source, pos, pixel):
        """Called automatically by FullShape.__getitem__

        Only implemented for pixels with all attributes (used by fullshape)
        """
        pcls = type(pixel)
        values = list(pixel)

        def build_args(channel, signature):
            nonlocal transformer, pixel, values, ch_num
            args = {}
            for parameter in signature:
                if parameter == "self":
                    args["self"] = transformer
                elif parameter == "value":
                    args["value"] = values[ch_num]
                elif parameter in Transformer.channels:
                    args[parameter] = getattr(pixel, parameter if parameter != "char" else "value")
                elif parameter == "pos":
                    args["pos"] = pos
                elif parameter == "pixel":
                    args["pixel"] = pixel
                elif parameter == "source":
                    args["source"] = source
                elif parameter == "tick":
                    args["tick"] = getattr(context, "tick", 0)
                elif parameter == "context":
                    args["context"] = source.context
            return args

        # TODO: if composite spatial != identity, fetch each pixel from source.

        for transformer in self.stack:
            values = list(pixel)
            for ch_num, channel in enumerate(Transformer.channels):
                transformer_channel = getattr(transformer, channel, None)
                if not transformer_channel:
                    continue
                if not callable(transformer_channel):
                    values[ch_num] = transformer_channel
                    continue
                params = build_args(transformer_channel, transformer.signatures[channel])
                values[ch_num] = transformer_channel(**params)
            pixel = pcls(*values)
        return pixel


"""
Doc string of old-style "transform-on-write" 'create_transformer'  - kept transitionally
due to the examples and ideas for transformers.



    ex. to install a transformer to force all text effects off:
    ```
    from terminedia values import create_transformer, NOP, Effects
    ...
    create_transformer(shape.context, [NOP, NOP, NOP, Effects.none])
    ```

    For a transformer that will force all color rendering
    to be done to the background instead of foreground:
    ```
    create_transformer(shape.context, [NOP, TRANSPARENT, lambda pos, values, context: values[1], NOP])
    ```

    Transfomer to make all printed numbers be printed blinking:

    ```
    create_transformer(shape.context, [NOP, NOP, NOP, lambda pos, values, context: Effects.blink if values[0].isdigit() else TRANSPARENT])
    ```



"""
