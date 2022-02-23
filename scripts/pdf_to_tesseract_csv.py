import pandas as pd
import os
from pdf2image import convert_from_path, pdfinfo_from_path
import multiprocessing
import pytesseract
import time

# enable multiprocessing for tesseract
os.environ['OMP_THREAD_LIMIT'] = '1'
CURRENT_FILE_PATH = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = CURRENT_FILE_PATH + '/../data/processed/tesseract_csvs/'


def save_tesseract_output_to_csv(textbook, pages_texts):
    texts_df = [pages_texts[page_num] for page_num in sorted(pages_texts.keys())]
    pd.concat(texts_df).to_csv(f'{OUTPUT_PATH}{textbook}.csv', index=False)        

def get_text_data(page_number, page_image, page_texts):
    # Adding custom options
    custom_config = r'--oem 3 --psm 6'
    result = pytesseract.image_to_data(page_image, config=custom_config, output_type='data.frame')
    result.loc[:, 'page_num'] = page_number
    page_texts[page_number] = result
    

def convert_images_to_text(start_page, images):
    page_texts = multiprocessing.Manager().dict()
    pool = multiprocessing.Pool(multiprocessing.cpu_count())

    for i, page_image in enumerate(images):
        pool.apply_async(get_text_data, args=(start_page+i, page_image, page_texts))

    pool.close()
    pool.join()

    return page_texts


def get_page_images(textbooks_dataset, textbook, page_chunks):
    path = os.path.join(textbooks_dataset, textbook)
    info = pdfinfo_from_path(path, userpw=None, poppler_path=None)
    max_pages = info['Pages']
    for start_page in range(1, max_pages+1, page_chunks):
        end_page = min(start_page+page_chunks-1, max_pages)
        yield (start_page, end_page, convert_from_path(path, first_page=start_page, last_page=end_page))



def pdf_to_tesseract_csvs():
    textbooks_dataset = CURRENT_FILE_PATH + '/../data/external/textbooks_archive/data/'
    metadata_csv = CURRENT_FILE_PATH + '/../data/external/textbooks_archive/Metadata.csv'
    page_chunk_size = 100

    metadata = pd.read_csv(metadata_csv)
    textbooks = [file_name for file_name in metadata.loc[metadata['Contents Page'].notnull()]['File_name']]

    textbooks_str = '\n'.join(textbooks)

    for textbook in textbooks:
        print(f"Converting {textbook}")

        pages_texts = {}
        page_chunks = get_page_images(textbooks_dataset, textbook, page_chunk_size)
        for start_page, end_page, page_chunk in page_chunks:
            pages_texts.update(convert_images_to_text(start_page, page_chunk))
            print(f"Finished converting {textbook} for pages {start_page} - {end_page}")

        save_tesseract_output_to_csv(textbook, pages_texts)


start_time = time.time()
pdf_to_tesseract_csvs()
print(f"--- {(time.time() - start_time)} seconds ---")
