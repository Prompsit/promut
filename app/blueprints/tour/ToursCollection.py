class ToursCollection(object):
    tours = {
        'library/corpora': {
            'tour_title': 'Welcome to Promut. Let\'s get started by grabbing a public dataset or uploading a new one. Datasets will be used to train NMT engines.'
        },
        'library/engines': {
            'tour_title': 'You are in the Engines section now. Here, you can grab public engines or see your own, once you complete a training. Engines in your list will be used in Translate and Inspect sections.'
        },
        'train': {
            'tour_title': 'It looks like you want to train an engine. Do you want help?',
            'tooltips': True,
            'popovers': [
                {
                    'element': 'nameText',
                    'title': 'Name your neural engine'
                },
                {
                    'element': 'source_lang',
                    'title': 'Source and target languages',
                    'description': 'Choose the source and target language of your neural engine. Make sure you have datasets available for the selected languages.'
                },
                {
                    'element': 'descriptionText',
                    'title': 'Description',
                    'description': 'You can write a brief description about your neural engine. Maybe you can say whether it is a generic or a custom engine.'
                },
                {
                    'element': 'epochsText',
                    'title': 'Duration',
                    'description': 'This is the amount of epochs allowed in the training process. An epoch is a full training pass over the whole amount of sentences in the training set. Set it between 4 and 10 epochs in Promut.'
                },
                {
                    'element': 'patienceGroup',
                    'title': 'Stopping condition',
                    'description': 'Your engine will stop if it does not improve after a set amount of validations. Our tip for Promut is to set it between 3 and 5. You can also stop the engine manually at any time.'
                },
                {
                    'element': 'validationFreq',
                    'title': 'Validation frequency',
                    'description': 'The amount of steps included before an evaluation of the status of the training takes place. Validation cycles happen many times inside an epoch. A validation every 600 and 1200 steps is what we recommend for Promut depending on dataset size.'
                },
                {
                    'element': 'vocabularySizeGroup',
                    'title': 'Vocabulary size',
                    'description': 'The amount of words in the vocabulary is known as the vocabulary size. Set it between 16000 and 32000 (sub-)words in Promut.'
                },
                {
                    'element': 'batchSizeTxt',
                    'title': 'Batch size',
                    'description': 'The amount of sentences processed in each step is known as the batch size. This is needed because it is not possible to give the full amount of data in the training set to the neural network at once. Try with batch sizes between 16 and 128 sentences with Promut.'
                },
                {
                    'element': 'beamSizeTxt',
                    'title': 'Beam size',
                    'description': 'Number of translation hypothesis taken into account when translating a word. Set it between 6 to 8 in Promut.'
                },
                {
                    'element': 'corpus-selector',
                    'title': 'Corpus selector',
                    'description': 'You almost have it! The last step is to choose the datasets for the training, validation and test processes. You can choose a whole dataset or just a part of it. When you have it clear, click on the plus sign (+)'
                }
            ]
        },
        'finetune': {
            'tour_title': 'It looks like you want to finetune an OPUS engine. Do you want help?',
            'tooltips': True,
            'popovers': [
                {
                    'element': 'nameText',
                    'title': 'Name your neural engine'
                },
                {
                    'element': 'source_lang',
                    'title': 'Source and target languages',
                    'description': 'Choose the source and target language of your neural engine. Make sure you have datasets available for the selected languages.'
                },
                {
                    'element': 'descriptionText',
                    'title': 'Description',
                    'description': 'You can write a brief description about your neural engine.'
                },
                {
                    'element': 'engine_name',
                    'title': 'Model',
                    'description': 'Choose the OPUS model you wish to finetune for the selected language pair. You must have first "grabbed" a public OPUS model in the Engines tab'
                },
                {
                    'element': 'epochsText',
                    'title': 'Duration',
                    'description': 'This is the amount of epochs allowed in the training process. An epoch is a full training pass over the whole amount of sentences in the training set. Set it between 4 and 10 epochs in Promut.'
                },
                {
                    'element': 'patienceGroup',
                    'title': 'Stopping condition',
                    'description': 'Your engine will stop if it does not improve after a set amount of validations. Our tip for Promut is to set it between 3 and 5. You can also stop the engine manually at any time.'
                },
                {
                    'element': 'validationFreq',
                    'title': 'Validation frequency',
                    'description': 'The amount of steps included before an evaluation of the status of the training takes place. Validation cycles happen many times inside an epoch. A validation every 600 and 1200 steps is what we recommend for Promut depending on dataset size.'
                },
                {
                    'element': 'vocabularySizeGroup',
                    'title': 'Vocabulary size',
                    'description': 'Vocabulary for finetuning is not customizable, as it depends completely on the already generated vocabulary of the downloaded OPUS models.'
                },
                {
                    'element': 'batchSizeTxt',
                    'title': 'Batch size',
                    'description': 'Batch sizes for finetuning are not customizable, given the vast size of OPUS models. This is left internally to Marian to optimize batch sizes during training.'
                },
                {
                    'element': 'beamSizeTxt',
                    'title': 'Beam size',
                    'description': 'Beam size for finetuning is not customizable, and instead the one set by the OPUS authors in the OPUS model configuration is used.'
                },
                {
                    'element': 'corpus-selector',
                    'title': 'Dataset selector',
                    'description': 'You almost have it! The last step is to choose the datasets for the training, validation and test processes. You can choose a whole dataset or just a part of it. When you have it clear, click on the plus sign (+)'
                }
            ]
        },
        'translate': {
            'tour_title': 'Time to see NMT engines at work: translate using one of your available engines or two concatenated (see + button). You can translate a bunch of sentences or a document. Is the result up to your expectations?'
        },
        'inspect/details': {
            'tour_title': 'In this section, you can see how a neural engine works and compare it to others. Ideas on how to improve the results?',
            'popovers': [
                {
                    'element': 'detailsBtn',
                    'title': 'Details',
                    'description': 'Write a sentence, choose a neural engine and take a look at the whole translation process, from how it analyses that sentence to how it gives you the resulting translation.'
                },
                {
                    'element': 'compareBtn',
                    'title': 'Compare',
                    'description': 'Write a sentence, choose a neural engine and compare the resulting translation with another neural engine. Both engines must have the same source and target languages.'
                },
                {
                    'element': 'accessBtn',
                    'title': 'Access',
                    'description': 'Yet to come!'
                }
            ]
        },
        'evaluate': {
            'tour_title': 'As the name suggests, here you can evaluate translations made by machine translation engines against professional translations. You will also get familiar with automatic metrics!',
            'tooltips': True,
            'popovers': [
                {
                    'element': 'source_file',
                    'title': 'Source file (optional)',
                    'description': 'Original text should be plain text or TMX'
                },
                {
                    'element': 'mt_file',
                    'title': 'Machine translation',
                    'description': 'Translation made by the neural engine. It should be plain text or TMX.'
                },
                {
                    'element': 'ht_file',
                    'title': 'Reference translation',
                    'description': 'Translation performed by a professional. It should be plain text or TMX.'
                },
                {
                    'element': 'ttr-badge',
                    'title': 'TTR',
                    'description': 'Type Token Ratio indicates relationship between the number of types (unique words) and the number of tokens (total number of words) in a text.'
                },
                {
                    'element': 'sample-bleu',
                    'title': 'BLEU',
                    'description': '% of word n-grams of the reference file present in the MT file.'
                },
                {
                    'element': 'sample-chrf3',
                    'title': 'chrF3',
                    'description': '% of characters n-grams of the reference file present in the MT file.'
                },
                {
                    'element': 'sample-ter',
                    'title': 'TER',
                    'description': '% of characters needing modification in the MT file in order to match the reference file.'
                }
            ]
        }
    }

    @staticmethod
    def has(tour_id):
        return tour_id in ToursCollection.tours.keys()

    @staticmethod
    def get(tour_id):
        if ToursCollection.has(tour_id):
            return ToursCollection.tours[tour_id]
        else:
            return None