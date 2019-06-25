import codecs                                   # codecs专门用作编码转换
from setuptools import setup


with codecs.open('README.rst', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="shadowsocks",
    version="2.8.2",
    license='http://www.apache.org/licenses/LICENSE-2.0',
    description="A fast tunnel proxy that help you get through firewalls",
    author='clowwindy',
    author_email='clowwindy42@gmail.com',
    url='https://github.com/shadowsocks/shadowsocks',
    packages=['shadowsocks', 'shadowsocks.crypto'],     # 需要处理的包目录
    package_data={
        'shadowsocks': ['README.rst', 'LICENSE']
    },
    install_requires=[],                                # 需要安装的依赖包
    # 动态发现服务和插件，console_scripts 指明了命令行工具的名称
    entry_points="""                                    
    [console_scripts]
    sslocal = shadowsocks.local:main
    ssserver = shadowsocks.server:main
    """,
    # 程序的所属分类列表
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: Proxy Servers',
    ],
    long_description=long_description,
)
