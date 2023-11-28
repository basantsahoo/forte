import yaml
import os


class YAMLLoader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(YAMLLoader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r') as f:
            return yaml.load(f, YAMLLoader)


YAMLLoader.add_constructor('!include', YAMLLoader.include)
