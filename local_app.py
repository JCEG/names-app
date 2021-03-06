import logging
import os
import pickle

import click
import numpy as np

import data
import model

@click.group()
@click.option('--log',
    default='INFO',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']),
    help="logging level to use during the application")
@click.pass_context
def main(ctx, log):
    ctx.obj = {'log': log}
    logging.basicConfig(level=log)

    logging.debug("Program started")

@main.command('train')
@click.option('--dataset-fpath',
    default=data.DEFAULT_FPATH,
    help="File path of a .hdf5 file with the data")
@click.option('--max-depth', type=int,
    help="Maximum depth of the tree")
@click.option('-a', '--all-data', is_flag=True,
    help="Wether to use all data available for training")
@click.option('-m', '--model-fpath',
    default=model.DEFAULT_FPATH,
    help="File path to store the model")
@click.option('-n', '--name', default='tree',
    help="name of the model to use from the registry")
@click.option('-t', '--test', is_flag=True,
    help="Wether to logg the accuracy on the test set")
@click.pass_context
def train(ctx, dataset_fpath, all_data, max_depth, model_fpath, name, test):

    if not os.path.isfile(dataset_fpath):
        logging.info('No dataset was provided, building with default settings')
        data.save_dataset(dataset_fpath)

    dataset = data.load_dataset(dataset_fpath, return_arrays=False) 
    clf = model.REGISTRY[name](max_depth=max_depth)

    X_train, y_train = dataset['X_train'], dataset['y_train']
    X_test, y_test = dataset['X_test'], dataset['y_test']
    if all_data:
        X_train = np.concatenate((X_train, X_test), axis=0)
        y_train = np.concatenate((y_train, y_test), axis=0)

    clf.fit(X_train, y_train)

    model.save_model(clf, model_fpath)

    acc = clf.score(X_train, y_train)
    logging.info("Accuracy on training set: {}".format(acc))

    if test:
        acc = clf.score(X_test, y_test)
        logging.info("Accuracy on the test set: {}".format(acc))

@main.command('test')
@click.option('-m', '--model-fpath',
    default=model.DEFAULT_FPATH,
    help="File path of a saved model")
@click.option('-d', '--dataset-fpath',
    default=data.DEFAULT_FPATH,
    help="File path of a .hdf5 file with the data")
@click.pass_context
def test(ctx, model_fpath, dataset_fpath):
    clf = model.load_model(model_fpath)
    
    dataset = data.load_dataset(dataset_fpath, return_arrays=False)
    acc = clf.score(dataset['X_test'], dataset['y_test'])
    logging.info("Accuracy on the test set: {}".format(acc))

@main.command('infer')
@click.argument('name')
@click.option('-m', '--model-fpath',
    default=model.DEFAULT_FPATH,
    help="File path of the model to use")
@click.pass_context
def infer(ctx, name, model_fpath):
    clf = model.load_model(model_fpath)

    parsed_name = data.infer_input_fn(name)

    label = clf.predict(parsed_name)
    logging.debug(label)

    label = data.parse_output(label)
    logging.info(label)

@main.command('download-data')
@click.option('-f', '--fpath',
    default=data.DEFAULT_FPATH,
    help="File path to store the data")
@click.pass_context
def download_data(ctx, fpath):
    data.save_dataset(fpath)


@main.command('export-model')
@click.option('-l', '--local-fpath',
    default=model.DEFAULT_FPATH,
    help="Path of the pickled model to be exported")
@click.option('-s', '--s3-fpath',
    default="srcolinas-names/models/model.pkl",
    help="S3 file path")
@click.pass_context
def export_model(ctx, local_fpath, s3_fpath):

    clf = model.load_model(local_fpath)

    import boto3
    bucket_name, key = s3_fpath.split('/', 1)
    s3 = boto3.resource('s3')
    s3.Object(bucket_name, key).put(Body=pickle.dumps(clf))
    
    
if __name__ == '__main__':
    main(obj={})