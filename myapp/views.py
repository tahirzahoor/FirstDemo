from http.client import SERVICE_UNAVAILABLE
import json
import math
import os
from pickle import TRUE
import re
import time
from django.shortcuts import get_object_or_404, render
from django.shortcuts import HttpResponse
import pymongo
from .models import Product, ProductImage
from rest_framework import generics
from .serializers import ProductSerializer
import requests
import logging
from selenium import webdriver
from bs4 import BeautifulSoup
import logging
import requests
from django.http import JsonResponse
from selenium.webdriver.common.keys import Keys 
from django.core.serializers import serialize
# Get logger instance
logger = logging.getLogger(__name__)


def serialize_document(document):
    # Convert ObjectId to string representation
    if '_id' in document:
        document['_id'] = str(document['_id'])
    return document


def get_products(request):
    try:
        page = int(request.GET.get('page', 1))
        print(page)
        size = int(request.GET.get('size', 10))
        skip = (page - 1) * size
        products = []

        db = getbd()
        collection = db['products']
        collection.create_index([("name", "text"), ("description", "text")])
        
        query = {}
        for key, value in request.GET.items():
            if key == "page" or key == "size" or key == "description":
                continue
            elif key == "price" or key == "rating":
                query[key] = float(value)
            elif key == "total_rates" or key == "views":
                query[key] = int(value)
            elif key == "search":
             query["$or"] = [
                {"name": {"$regex": value, "$options": "i"}},
                {"description": {"$regex": value, "$options": "i"}},
                {"brand": {"$regex": value, "$options": "i"}},
    
                ]
            else:
                query[key] = {"$regex": value, "$options": "i"}

        cursor = collection.find(query).skip(skip).limit(size)
        products = [serialize_document(doc) for doc in cursor]

        # Get total number of documents matching the query
        total_count = collection.count_documents(query)
        
        # Calculate total number of pages
        total_pages = math.ceil(total_count / size)

        # Metadata about the page
        meta = {
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "total_items": total_count
        }

        response = {
            "products": products,
            "meta": meta
        }

        return JsonResponse(response, safe=False)
    except Exception as e:
        error_message = "Error during scraping: {}".format(str(e))
        logger.error(error_message)
        return HttpResponse(error_message, status=500)


def scrape_and_save(request):
    queryBrand = request.GET.get('brand', '')
    print("queryBrand "+ queryBrand)
    products = []
    try:
       if queryBrand == "hm":
       ## products = getHmProducts()
        products = verifyBrandSupport()
       elif queryBrand == "zara":
        products = getZaraAllProducts()
       elif queryBrand == "asos":
        products = scrapAsosBrand()
       elif queryBrand == "vinted":
        products = getFullProfile("https://www.vinted.co.uk/member/136748494-rachg2103")
       return JsonResponse(products, safe=False)

    except Exception as e:
        error_message = "Error during scraping: {}".format(str(e))
        logger.error(error_message)
        return HttpResponse(error_message, status=500)


def scrapAsosBrand():

    db= getbd()
    collection = db['products']

    products = []
    catUrls = getAsosAllCatUrls()
    # url = "https://www.asos.com/asos-design/asos-design-square-neck-pleat-bust-midi-pencil-dress-in-deep-green/prd/205193080#colourWayId-205193081"
    # product = getAsosProduct(url)
    # products.append(product)
    
    for catUrl in catUrls:
        catProductsUrls= getAsosCatAllProductsUrls(catUrl)
        for catProductsUrl in catProductsUrls:
            product = getAsosProduct(catProductsUrl)
            if product != None:
             collection.insert_one(product)
             products.append(product)
    return products
    


def getAsosAllCatUrls():
    # return ["https://www.asos.com/women/dresses/cat/?cid=8799",
    #         "https://www.asos.com/women/shoes/cat/?cid=4172",
    #         "https://www.asos.com/women/accessories/cat/?cid=4174",
    #         "https://www.asos.com/women/face-body/cat/?cid=1314"]
     return ["https://www.asos.com/women/dresses/cat/?cid=8799"]

def getAsosCatAllProductsUrls(catUrl):
    productUrls = []
    condition = True
    pageNumber = 1
    while condition:
        url = catUrl + "&page={}".format(pageNumber)
        print("pageUrl", url)
        try:
            soup = getSoap(url)
            eProducts = soup.find_all('a', class_='productLink_KM4PI')
            for eProduct in eProducts:
                productUrls.append(eProduct.get('href'))
            pageNumber += 1
        except Exception as e:
            print("An error occurred:", str(e))
        condition = False
    return productUrls

def getAsosProduct(productUrl):
    try:
        product = {}
        soup = getSoap(productUrl)

        product["brand"] = "ASOS" 
        product["condition"] = "Brand new"
        product["name"] = soup.find(class_='jcdpl').text
        #print("ASOSPoduct",  soup.find("h1", class_='jcdpl').text)
        product["price"] = string_to_float(soup.find( class_='MwTOW').text)
        product["currency_sign"] = "£"
        ratingDetail = soup.find(class_='JO8_V').text.split("(")
        product["rating"] = float(ratingDetail[0])
        product["total_rates"] = int(ratingDetail[1].replace(")",""))
        ePictures = soup.find_all("div", class_='fullImageContainer')
        pictures = []
        for catUrl in ePictures:
            imageTag = catUrl.find("img", class_='img')
            if imageTag:
                image_src = imageTag.get('src')
                pictures.append(image_src)  # Append source URL of image
        product["pictures"] = pictures
        product["description"] = "Description"
        product["shipping_exchanges_returns"] = ""
        product["payment_options"] = ""
        product["views"] = 0
        product["colors"] = []
        product["sizes"] = []

        return product

    except Exception as e:
        print("ProductException: " + str(e))
        return None



# product_details = {
#     "brand": "Zara",
#     "condition": "Brand new",
#     "name": "Product Name",
#     "price": "$100",
#     "description": "Product Description",
#     "shipping_exchanges_returns": "Free shipping",
#     "size": "M",
#     "payment_options": "Credit card, PayPal",
#     "views": 100,
#     "colors": [{"name": "Red", "color_code": "#ff0000"}],
#     "sizes": [{"size": "M", "is_available": True}],
#     "pictures": ["image1.jpg", "image2.jpg"]
# }

def getCharFromString(input_string):
    cleaned_string = ''.join(filter(str.isalpha, input_string))
    return cleaned_string
    
def string_to_float(input_string):
    cleaned_string = ''.join(filter(str.isdigit, input_string))
    integer_number = float(cleaned_string)
    
    return integer_number

def string_to_integer(input_string):
    cleaned_string = ''.join(filter(str.isdigit, input_string))
    integer_number = int(cleaned_string)
    
    return integer_number

def getHmProducts1():
    products = []
    condition = True
    pageNumber = 1
    while condition:
        url = "https://www2.hm.com/en_gb/ladies/shop-by-product/view-all.html?page={}".format(pageNumber)
        print("PageNumber", url)
        soup = getSoap(url)
        eProducts = soup.find_all(class_='eed2a5 ec329a')
        pProducts = []
        for eProduct in eProducts:
            edetails = eProduct.find_all('a', class_='db7c79')
            for edetail in edetails:
                pProducts.append({'url': edetail.get('href')})
        products.extend(pProducts)
        if not pProducts:
            condition = False

        if pageNumber == 3:
            condition = False
        pageNumber = pageNumber+1
    return products





##Zaran Brand
    
   # zds-carousel-item layout-categories__carousel-item
    



def getZaraAllProducts():
    products = []
    db= getbd()
    collection = db['products']
    catLinks =  getZaraAllCatUrl()
    for catLink in catLinks:
        catsProduct = getZaraAllProductsUrls([catLink])
        for catProduct in catsProduct:
                product =  getZaraProductDetail(catProduct)
                if product != None:
                    products.append(product)
                    collection.insert_one(product)
    return catsProduct


def getZaraAllCatUrl():
    products = []
    url = "https://www.zara.com/uk/"
    print("PageNumber", url)
    soup = getSoap(url)
    print("soup", soup)
    cats = soup.find_all(class_='zds-carousel-item layout-categories__carousel-item')
    for cat in cats:
        print("eProduct", cat)
        subCats = cat.find_all('a', class_='layout-categories-category__link link')
        for subCat in subCats:
             url = subCat.get('href')
             if(url is not None):
                products.append(subCat.get('href'))
    return products

def getZaraAllProductsUrls(catLinks):
    products = []
    for url in catLinks:
        print("PageNumber", url)
        soup = getSoap(url)
        prductsLinks = soup.find_all('a', class_='product-link product-grid-product__link link')
        for prductsLink in prductsLinks:
            url =  prductsLink.get('href')
            products.append(url)
    return products


def getZaraProductDetail(productUrl):
    try:
        product = {}
        soup = getSoap(productUrl)
        
        productDiv = soup.find('div', class_='product-detail-view__main')
        product["brand"] ="Zara"
        product["condition"] = "Brand new"
        product["name"]  = productDiv.find(class_='product-detail-info__header-name').text.strip()
        product["price"] = string_to_float(productDiv.find(class_="money-amount__main").text.strip())
        expandable_text_div = productDiv.find('div', class_="product-detail-description product-detail-info__description")
        if expandable_text_div:
            product["description"] = expandable_text_div.text.strip()
        product["shipping_exchanges_returns"] = productDiv.find('div', class_="zds-dialog-content zds-drawer-content")
        product['size'] = ''
        product['payment_options'] = ""
        product["views"] = 0
        
        colorsDiv = soup.find_all('div', class_='product-detail-color-selector__color-area')
        colors = []
        for colorDiv in colorsDiv:
            # Extract inline CSS style attribute
            style_attribute = colorDiv['style']
            # Extract the background color value from the style attribute
            start_index = style_attribute.find('background-color: ') + len('background-color: ')
            end_index = style_attribute.find(';', start_index)
            background_color = style_attribute[start_index:end_index].strip()
            colors.append({'name': colorDiv.text.strip(), 'color_code': background_color})
            
        product["colors"] = colors

        sizesdDiv = soup.find_all(class_='size-selector-list__item')
        sizes = []
        for sizeDiv in sizesdDiv:
            classes = sizeDiv.get('class', [])
            is_available = 'size-selector-list__item--is-disabled' not in classes and 'size-selector-list__item--out-of-stock' not in classes
            sizes.append({'size':sizeDiv.text.strip(), "is_available":is_available })
        product["sizes"] = sizes

        product["url"] = productUrl

        pictures = []

        picutres_div = soup.find_all(class_='media__wrapper media__wrapper--fill media__wrapper--force-height')
        pictures = []
        # for picutre_div in picutres_div:
        #     picture_tags = picutre_div.find(class_="media-image__image media__wrapper--media")
        #     #picture_tags = soup.find_all('picture', class_='media-image')
        for picture_tag in picutres_div:
                source_tags = picture_tag.find_all('source')
                picture = []
                for source_tag in source_tags:
                    srcset = source_tag.get('srcset')
                    urls_and_sizes = re.findall(r'([^,\s]+)\s(\d+w)', srcset)
                    for url, size in urls_and_sizes:
                        picture.append(url)
                    first_picture_url = picture[0]
                pictures.append(first_picture_url)
        product["pictures"] = pictures
        
        return product

    except Exception as e:
        return None

def getZaraAllProductDetail1(productUrl):
    product = {}
    soup = getSoap(productUrl)
    
    productDiv = soup.find('div', class_='product-detail-view__main')
    product["brand"] ="Zara"
    product["condition"] = "Brand new"
    product["name"]  = productDiv.find(class_='product-detail-info__header-name').text.strip()
    product["price"] = productDiv.find(class_="money-amount__main").text.strip()
    expandable_text_div = productDiv.find('div', class_="product-detail-description product-detail-info__description")
    if expandable_text_div:
        product["description"] = expandable_text_div.text.strip()
    product["shipping_exchanges_returns"] = productDiv.find('div', class_="zds-dialog-content zds-drawer-content")
    product['size'] = ''
    product['payment_options'] = ""
    product["views"] = 0
    
    colorsDiv = soup.find_all('div', class_='product-detail-color-selector__color-area')
    colors = []
    for colorDiv in colorsDiv:
        # Extract inline CSS style attribute
        style_attribute = colorDiv['style']
        # Extract the background color value from the style attribute
        start_index = style_attribute.find('background-color: ') + len('background-color: ')
        end_index = style_attribute.find(';', start_index)
        background_color = style_attribute[start_index:end_index].strip()
        colors.append({'name': colorDiv.text.strip(), 'color_code': background_color})
        
    product["colors"] = colors

 

    #sizesdDiv = soup.find_all(class_='size-selector-list__item:not([class*="is-disabled"]):not([class*="out-of-stock"])')
    sizesdDiv = soup.find_all(class_='size-selector-list__item')
    sizes = []
    for sizeDiv in sizesdDiv:
        classes = sizeDiv.get('class', [])
        print("ProductClasses", classes)
        is_available = 'size-selector-list__item--is-disabled' not in classes and 'size-selector-list__item--out-of-stock' not in classes
        sizes.append({'size':sizeDiv.text.strip(), "is_available":is_available })
    product["sizes"] = sizes

    #media__wrapper media__wrapper--fill media__wrapper--force-height
    picutres_div = soup.find_all(class_='media__wrapper media__wrapper--fill media__wrapper--force-height')
    pictures = []
    for picutre_div in picutres_div:
         pictures.append(picutre_div.find(class_="media-image__image media__wrapper--media").get('src'))
    product["pictures"] = pictures
    print("product", product)
    return product


#  if title and value:
#                 if title.text.strip().lower()  == "brand": 
#                     item['brand'] = value.text.strip()
#                 if title.text.strip().lower()  == "size": 
#                     item['size'] = value.text.strip()
#                 if title.text.strip().lower()  == "condition": 
#                     item['condition'] = value.text.strip()
#                 if title.text.strip().lower()  == "payment options": 
#                     item['payment_options'] = value.text.strip()
#                 if title.text.strip().lower()  == "views": 
#                     item['views'] = value.text.strip()
#                 if title.text.strip().lower()  == "uploaded": 
#                     item['uploaded_date'] = value.text.strip()





def getZaraProducts():
    products = []
    url = "https://www.zara.com/uk/en/woman-jackets-l1114.html?v1=2352724"
    print("PageNumber", url)
    soup = getSoap(url)
    print("soup", soup)
    eProducts = soup.find_all('a',class_='product-link product-grid-product__link link')
    for eProduct in eProducts:
        products.append({'url': eProduct.get('href')})
        # edetails = eProduct.find_all('a', class_='db7c79')
        # for edetail in edetails:
        #     products.append({'url': edetail.get('href')})
    return products

##Revolve Brand

def getRevolveProducts():
    products = []
    # condition = True
    # pageNumber = 1
    # while condition:
    url = "https://www.revolve.com/new/20240306/br/df6edc/?navsrc=main"
    print("PageNumber", url)
    soup = getSoap(url)
    eContainers = soup.find_all(class_='g products-grid u-margin-b--xxl block-grid--inline n-block-grid--3 lg-block-grid--4 js-plp-lazy-load')
    for eContainer in eContainers:
        eProducts = eContainer.find_all('a',class_='js-plp-pdp-link plp__image-link plp__image-link--lg')
        for eProduct in eProducts: 
            products.append({'url': eProduct.get('href')})
        # edetails = eProduct.find_all('a', class_='db7c79')
        # for edetail in edetails:
        #     products.append({'url': edetail.get('href')})
       
    return products



##Hm Brand
def getHmProducts():
    products = []
    condition = True
    pageNumber = 1
    while condition:
        url = "https://www2.hm.com/en_gb/ladies/shop-by-product/view-all.html?page={}".format(pageNumber)
        print("PageNumber", url)
        soup = getSoap(url)
        eProducts = soup.find_all(class_='eed2a5 ec329a')
        pProducts = []
        for eProduct in eProducts:
            edetails = eProduct.find_all('a', class_='db7c79')
            for edetail in edetails:
                pProducts.append({'url': edetail.get('href')})
        products.extend(pProducts)
        if not pProducts:
            condition = False

        if pageNumber == 3:
            condition = False
        pageNumber = pageNumber+1
    return products



def scrape_and_save111(request):
    try:
        #scrape_clothing_website11()
    #     response = requests.get('https://www.vinted.co.uk/catalog')
    #     soup = BeautifulSoup(response.text, 'html.parser')
    #     #web_ui__Cell__cell web_ui__Cell__default
    #     # member_explore1=soup.find_all(class_='web_ui__Cell__title')
    #     # for member1 in member_explore1:
    #     #     member_explore=member1.find_all(class_='web_ui__Button__button web_ui__Button__outlined web_ui__Button__small web_ui__Button__primary web_ui__Button__truncated')
    #     #     products = []
    #     #     for member in member_explore:
    #     #         hrf= member.get('href')
    #     #         products.append({'hrf':hrf })
    #     # return JsonResponse(products, safe=False)
    #    # web_ui__Cell__cell web_ui__Cell__default
    #     #member_explore1=soup.find_all(class_='feed-grid__item')
    #     product_containers = soup.find(class_='site-content__content-section')
    #     product_containers1 = product_containers.find_all(class_='feed-grid')
        
    #     #member_explore1 = product_containers1.find_all(class_='feed-grid__item')
    
    #     logger.info("Scraping status code: %s", product_containers)
        # products = [{'hrf':soup.text }]
        # for member in product_containers1:
        #         hrf= member.get('href')
        #         products.append({'hrf':soup.text })

        #url = "https://www.vinted.co.uk/" #"https://www.asos.com/women/new-in/cat/?cid=27108"
       # response = requests.get(url)
        ##raise Exception(str(response))
        #responseStatus = "Response code: {}".format(str(223))
       # soup = BeautifulSoup(response.text, 'html.parser')
        #response111 =  scrape_dynamic_content() #asosSrap()
        response = asosSrap()
        #response = getFullProfile("https://www.vinted.co.uk/member/187922410-mskellio")
        return JsonResponse(response, safe=False)
        
    #     url="https://www.vinted.co.uk"
    #     response = requests.get(url)
    #     logger.info("Scraping status code: %s", response.status_code)
        
    #     soup = BeautifulSoup(response.text, 'html.parser')
      
    #     categories = []
    #     product_containers = soup.find(class_='web_ui__Tabs__content')
    #     product_container17 = product_containers.find_all(class_='web_ui__Tabs__tab web_ui__Tabs__allow-overflow')
    
    #     for product_container in product_container17:
            
    #         cat_type = product_container.find(class_='nav-links')
    #         cat_title = cat_type.text.strip()
    #         cat_href = cat_type.get('href')
    #         cat_url = url + cat_href
    #         dropdown_menu = product_container.find(class_='catalog-dropdown__catalogs')
    #         if dropdown_menu:
    #             products = []
    #             product_items = dropdown_menu.find_all(class_='catalog-dropdown__category active')
    #             for product_item in product_items:
    #                 cats = product_item.find_all(class_='web_ui__Cell__cell web_ui__Cell__narrow web_ui__Cell__navigating web_ui__Cell__link')
    #                 for cat in cats:
    #                     title = cat.text.strip()
    #                     href = cat.get('href')
    #                     new_url = url + href
    #                     products.append({'name': title, 'price': 1,'hrf' : new_url})  # Assuming price is constant for now
    #             categories.append({'name': cat_title, 'href': cat_url, 'products': products})
        
    #     response_data = {'products': categories}
    #     return JsonResponse(response_data, safe=False)

    except Exception as e:
        error_message = "Error during scraping: {}".format(str(e))
        logger.error(error_message)
        return HttpResponse(error_message, status=500)

def verifyBrandSupport():
    url = "https://zlibrary.to"
    soup = getSoap(url)
    eProfileItems=soup.find_all('div')
   ## print(eProfileItems)
    profiles = []
    for eProfileItem in eProfileItems:
        eProfileItemContainers=eProfileItem.find_all(class_='jsx-c590bebd41c6ba4e collection-item')
        for eProfileItemContainer in eProfileItemContainers:
            profileUrlElements=eProfileItemContainer.find_all('img',class_='jsx-c590bebd41c6ba4e collection-img')
            for profileUrlElement in profileUrlElements:
                if profileUrlElement:
                    url=profileUrlElement.get('src')
                    profiles.append(url)
    return [profiles] 








def getVintedProfiles():
    url = "https://www.vinted.co.uk/catalog/1904-women"
    soup = getSoap(url)
    eProfileItems=soup.find_all(class_='feed-grid__item')
    profiles = []
    for eProfileItem in eProfileItems:
        eProfileItemContainers=eProfileItem.find_all(class_='new-item-box__container')
        for eProfileItemContainer in eProfileItemContainers:
            profileUrlElements=eProfileItemContainer.find_all('a',class_='web_ui__Cell__cell web_ui__Cell__narrow web_ui__Cell__link')
            for profileUrlElement in profileUrlElements:
                if profileUrlElement:
                    url=profileUrlElement.get('href')
                    profiles.append({'url':url})
    print(profiles)
    return [profiles]    

def getFullProfile(profileUrl):
    soup = getSoap(profileUrl)
    db= getbd()
    collection = db['products']
    eItems=soup.find_all(class_='u-ui-margin-horizontal-regular@portables')
    profle = {}
    items = []
    for eProfileItem in eItems:
        eProfileItemContainers=eProfileItem.find_all(class_='new-item-box__overlay new-item-box__overlay--clickable')
        for eProfileItemContainer in eProfileItemContainers:
                print(eProfileItemContainer.get("href"))
                item = getItemDetail(eProfileItemContainer.get("href"))
                if item != None:
                    collection.insert_one(item)
                items.append(item)

    profle['items'] = items
    #web_ui__Image__image web_ui__Image__x4-large web_ui__Image__circle web_ui__Image__scaled web_ui__Image__cover
    eProfilePic=soup.find('div',class_='web_ui__Image__image web_ui__Image__x4-large web_ui__Image__circle web_ui__Image__scaled web_ui__Image__cover')
    profle["profile_pic"] = eProfilePic.find('img','web_ui__Image__content').get('src')

    profle["name"] = soup.find('h1',"web_ui__Text__text web_ui__Text__heading web_ui__Text__left web_ui__Text__amplified web_ui__Text__bold").text.strip()

    print(profle)
    return profle    

def getItemDetail(itemUrl):
    soup = getSoap(itemUrl)
    item = {}

    priceDetails=soup.find(class_='box box--item-details')
    item['price'] = priceDetails.find(class_='web_ui__Text__text web_ui__Text__heading web_ui__Text__left').text.strip()
    item['protectedPrice'] = priceDetails.find(class_='web_ui__Text__text web_ui__Text__subtitle web_ui__Text__left web_ui__Text__clickable web_ui__Text__underline-none').text.strip()
    item['platform'] = "vinted"
    itemsDetails1=soup.find_all(class_='details-list details-list--details')
    for itemsDetail1 in itemsDetails1:
        itemsDetails=itemsDetail1.find_all('div')
        for itemsDetail in itemsDetails:
            title=itemsDetail.find(class_='details-list__item-title')
            value=itemsDetail.find(class_='details-list__item-value')
            print('----------------------------------------')
            print(itemsDetail)
            print('----------------------------------------')
            if title and value:
                if title.text.strip().lower()  == "brand": 
                    item['brand'] = value.text.strip().replace("Brand menu", "")
                if title.text.strip().lower()  == "size": 
                    item['size'] = value.text.strip().replace("Size information", "")
                if title.text.strip().lower()  == "condition": 
                    item['condition'] = value.text.strip().replace("Condition information", "")
                if title.text.strip().lower()  == "payment options": 
                    item['payment_options'] = value.text.strip()
                if title.text.strip().lower()  == "views": 
                    item['views'] = value.text.strip()
                if title.text.strip().lower()  == "uploaded": 
                    item['uploaded_date'] = value.text.strip()

    ePhotos=soup.find_all(class_='item-photos')
    photos = []
    for ePhoto in ePhotos:
        tphotos=ePhoto.find_all(class_='web_ui__Image__content')
        for tphoto in tphotos:
            #print(tphoto.get("src"))
            photos.append({'url':tphoto.get("src")})
    item['images'] = photos

    ## price Tag   web_ui__Text__text web_ui__Text__heading web_ui__Text__left
    ## Protect price detail :  web_ui__Text__text web_ui__Text__subtitle web_ui__Text__left web_ui__Text__clickable web_ui__Text__underline-none

    # eItems=soup.find_all(class_='item-photos')
  
    # for eProfileItem in eItems:
    #     eProfileItemContainers=eProfileItem.find_all(class_='new-item-box__overlay new-item-box__overlay--clickable')
    #     for eProfileItemContainer in eProfileItemContainers:
    #          # profileUrlElements=eProfileItemContainer.find_all('a',class_='web_ui__Cell__cell web_ui__Cell__narrow web_ui__Cell__link')
    #             print(eProfileItemContainer.get("href"))
    #             items.append({'url':eProfileItemContainer.get("href")})
    #     #     for profileUrlElement in profileUrlElements:
    #     #         if profileUrlElement:
    #     #             url=profileUrlElement.get('href')
    #     #             profiles.append({'url':url})
    #     ##profiles.append({'url':eProfileItemContainers})
      
    print(item)
    return item 


def getSoap1(url):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    # options.add_argument("--headless=new")
    options.add_argument('--disable-gpu') 
    options.add_argument('./chromedriver')
    # options.add_argument('--ignore-certificate-errors')
    # options.add_argument('disable-notifications')
    # options.add_argument('--disable-blink-features=AutomationControlled')
    driver = webdriver.Chrome(options=options)
    driver.get(url)  
    time.sleep(5)  
    html = driver.page_source
    print("*****************************")
  #  print(html)
    print("*****************************")
    return BeautifulSoup(html, "html.parser") 


# from fake_useragent import UserAgent
# from requests_html import HTMLSession
# from fake_useragent import UserAgent
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
def getSoap(url):
    options = webdriver.FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-blink-features=BrowserSideNavigation")
    options.add_argument("user-agent=Mozilla/126.0")
   
    #service = Service(ChromeDriverManager().install())

    driver = webdriver.Firefox(service= Service(GeckoDriverManager().install()), options=options)

    # service = SERVICE_UNAVAILABLE('./chromedriver')
    # driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url)
        time.sleep(5)  # Add a delay to ensure the page is fully loaded
        html = driver.page_source
        return BeautifulSoup(html, "html.parser")
    except Exception as e:
        print("Error accessing URL:", e)
    finally:
        driver.quit()

    # try:
    #     headers = {
    #         'User-Agent': UserAgent().random,
    #         'Accept-Language': 'en-US,en;q=0.9',
    #         'Accept-Encoding': 'gzip, deflate, br',
    #         'Connection': 'keep-alive',
    #         'Upgrade-Insecure-Requests': '1',
    #     }
            
    #     r = requests.get(url, headers=headers)
    #     r.raise_for_status()  # Raise HTTPError for bad responses

    #     ##r = requests.get(url)
    #     return BeautifulSoup(r.content, 'html.parser')
    # except Exception as e:
    #     print("Error accessing URL:", e)
    #     return None

    # ua = UserAgent()
    # headers = {
    #     'User-Agent': ua.random,
    #     'Accept-Language': 'en-US,en;q=0.9',
    #     'Accept-Encoding': 'gzip, deflate, br',
    #     'Connection': 'keep-alive',
    #     'Upgrade-Insecure-Requests': '1',
    # }

    # session = HTMLSession()
    # session.headers.update(headers)

    # try:
    #     response = session.get(url)
    #     #response.html.render(timeout=20)  # Render JavaScript with a timeout

    #     # Parse the rendered HTML using BeautifulSoup
    #     #soup = BeautifulSoup(response.html.html, 'html.parser')

    #     return BeautifulSoup(response.html.html, 'html.parser')
    # except Exception as e:
    #     print("Error accessing URL:", e)
    #     return None


from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from bs4 import BeautifulSoup  # Assuming BeautifulSoup is imported elsewhere
import time  # Optional: for adding a delay

def getSoap99(url):
    try:
        options = Options()
        #options.add_argument("--headless")  # Run Firefox in headless mode
        #options.add_argument("--disable-gpu")  # Disable GPU usage (optional)
        #options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        #options.add_argument("--disable-dev-shm-usage")
        #options.add_argument("--disable-blink-features=AutomationControlled")
        #options.add_argument("--disable-blink-features=BrowserSideNavigation")
        #options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        # Create a Firefox driver instance
        driver = webdriver.Firefox(options=options)
        driver.delete_all_cookies()
        driver.get(url)
        time.sleep(5)  # Adjust the delay as needed to ensure page load
        # Get the HTML source code
        html = driver.page_source
        # Parse the HTML with BeautifulSoup
        sp = BeautifulSoup(html, "html.parser")
        driver.quit()
        return sp
    except Exception as e:
        print("Error accessing URL:", e)





def method1():
    #url of the page we want to scrape 
    url = "https://www.vinted.co.uk/catalog/1904-women"
  
    # initiating the webdriver. Parameter includes the path of the webdriver. 
    # cService = webdriver.ChromeService(executable_path='./chromedriver')
    # driver = webdriver.Chrome(service = cService)

    # options = webdriver.ChromeOptions()
    # options.add_argument('./chromedriver')
    # driver = webdriver.Chrome(options=options)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # This line makes the browser run in headless mode
    options.add_argument('--disable-gpu')  # This line helps prevent issues in headless mode
    options.add_argument('./chromedriver')


    
    
    # Initiate the webdriver with the options and service
    driver = webdriver.Chrome(options=options)
    
    # cookies = [ {'name': 'cf_clearance', 'value': 'your_cookie_value', 'domain': '.wolfandbadger.com'},
    #            {'name': 'sessionid', 'value': 'your_cookie_value', 'domain': 'www.wolfandbadger.com'},
    #            {'name': 'DYID', 'value': 'your_cookie_value', 'domain': '.dynamicyield.com'}
    #            ]
    # driver.add_cookie( {'name': 'cf_clearance', 'value': 'your_cookie_value', 'domain': 'www.wolfandbadger.com'})
    # driver.add_cookie({'name': 'sessionid', 'value': 'your_cookie_value', 'domain': 'www.wolfandbadger.com'})
    # driver.add_cookie( {'name': 'DYID', 'value': 'your_cookie_value', 'domain': 'www.dynamicyield.com'})
   
    # driver.refresh()

    driver.get(url)  
    time.sleep(5)  
  
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser") 
    productsHtmml=soup.find_all(class_='feed-grid__item')
    products = []
    for product in productsHtmml:
        containers=product.find_all(class_='new-item-box__container')
        for container in containers:
            profileUrlElements=container.find_all('a',class_='web_ui__Cell__cell web_ui__Cell__narrow web_ui__Cell__link')
            for profileUrlElement in profileUrlElements:
                if profileUrlElement:
                    url=profileUrlElement.get('href')
                    products.append({'url':url})

        # name = product.find(class_='productDescription_sryaw').text.strip()
        # price = product.find(class_='container_s8SSI').text.strip()
        # detail = product.find(class_='sellingFastBadge_sYbXB').text.strip()
       
    
  #  error_message = "products1: {}".format(str(productsHtmml))
    print(products)
    return products    
    





def scrape_dynamic_content():
    # Initialize a headless browser
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    driver = webdriver.Chrome(options=options)

    try:
        # Navigate to the page with dynamic content
        driver.get('https://example.com')

        # Wait for dynamic content to load
        # Extract data using Selenium's find_element_* methods
       # element = driver.find_element_by_css_selector('.dynamic-element')
        #data = element.text
        data = []
        return [{'test':data}]
    finally:
        # Close the browser
        driver.quit()


def asosSrap():
    url = "https://www.asos.com/women/new-in/cat/?cid=27108"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    products = []
    for product in soup.find_all(class_='productTile_IAw3u'):
        name = product.find(class_='productDescription_sryaw').text.strip()
        price = product.find(class_='container_s8SSI').text.strip()
        detail = product.find(class_='sellingFastBadge_sYbXB').text.strip()
        products.append({'name': name, 'price': price, 'detail': detail})
    
    # error_message = "Error during scraping: {}".format(str(products))
    # logger.error(error_message)
    return products


def scrape_clothing_website11():
  
        # Configure Chrome options
        # options = Options()
        # options.add_argument('--headless')  # Run Chrome in headless mode, no GUI
        # options.add_argument('--disable-gpu')  # Disable GPU acceleration

        # Path to chromedriver executable
        chromedriver_path = '/path/to/chromedriver'  # Change this to the path of your chromedriver executable

        # Initialize Chrome webdriver
        driver = webdriver.Chrome()

        # Load the page
        driver.get('https://www.vinted.co.uk/catalog')
        driver.implicitly_wait(5)


        # Get page source after dynamically loaded content
        page_source = driver.page_source

        # Close the webdriver
        driver.quit()

        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Find all elements with class 'web_ui__Text__text web_ui__Text__caption web_ui__Text__left'
        member_explore = soup.find_all(class_='site-content__content-section')
        data=[]
        # Print all found elements
        for element in member_explore:
           item = element.find_all(class_='feed-grid')
           for element in item:
                data.append({'hrf':"hrf"})

        return data
    
    


def scrape_clothing_website():
    try:
        # Configure Chrome options
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Run Chrome in headless mode, no GUI
        options.add_argument('--disable-gpu')  # Disable GPU acceleration

        # Path to chromedriver executable
        chromedriver_path = '/path/to/chromedriver'  # Change this to the path of your chromedriver executable

        # Initialize Chrome webdriver
        driver = webdriver.Chrome(chromedriver_path, options=options)

        # Load the page
        driver.get('https://www.vinted.co.uk/catalog')

        # Get page source after dynamically loaded content
        page_source = driver.page_source

        # Close the webdriver
        driver.quit()

        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(page_source, 'html.parser')

        # Find all elements with class 'web_ui__Text__text web_ui__Text__caption web_ui__Text__left'
        member_explore = soup.find_all(class_='web_ui__Text__text web_ui__Text__caption web_ui__Text__left')
        products = []

        for member in member_explore:
            hrf = member.get('href')
            products.append({'hrf': hrf})

        return products
    
    except Exception as e:
        # Log the error
        logger.error("An error occurred: %s", e)
        # Return an empty list or any other indication of failure
        return []




#web_ui__Button__button web_ui__Button__outlined web_ui__Button__small web_ui__Button__primary web_ui__Button__truncated

class ProductList(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


def scrape_clothing_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    # for product in soup.find_all(class_='product'):
    #     name = product.find(class_='product-name').text.strip()
    #     price = product.find(class_='product-price').text.strip()
    #     products.append({'name': name, 'price': price})
    
    return products


def scrape_xos(url):
    response = requests.get(url)
    # print("Scraped data:", response)
    logger.info("Scraped data: %s", response)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = []
    # for product in soup.find_all(class_='product'):
    #     name = product.find(class_='product-name').text.strip()
    #     price = product.find(class_='product-price').text.strip()
    #     products.append({'name': name, 'price': price})
    
    return products


# def getbd():
#     # Initialize MongoDB client
#     client = pymongo.MongoClient("mongodb+srv://tahirzahoor456:KoVE5BUEkbixQUWb@cluster0.8ntl4e2.mongodb.net",serverSelectionTimeoutMS=30000)  # Update connection string as needed
#     db = client["shope"]  # Change "your_database_name" to your actual database name
#     return db  # Change "products" to your actual collection name

import pymongo
from pymongo import MongoClient

def getbd():
    # Initialize MongoDB client
    uri = "mongodb+srv://tahirzahoor456:KoVE5BUEkbixQUWb@cluster0.8ntl4e2.mongodb.net"
    # Create a new client and connect to the server
    client = MongoClient(uri)
    # Send a ping to confirm a successful connection
    try:
        client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
        db = client["shope"]  # Change "your_database_name" to your actual database name
        return db  # Change "products" to your actual collection name
    
    except Exception as e:
        print("Mongo roor",e)
        return None




def getVintitedCat():
    try:

        url = "https://www.vinted.co.uk/catalog"
        print("PageNumber", url)
        soup = getSoap(url)
        member_explore = soup.find_all(class_='site-content__content-section')
        data=[]
        # Print all found elements
        for element in member_explore:
           item = element.find_all(class_='feed-grid')
           for element in item:
                data.append({'hrf':"hrf"})

        return data
    
    except Exception as e:
        # Log the error
        logger.error("An error occurred: %s", e)
        # Return an empty list or any other indication of failure
        return []


















#############################################################3


def scrape_and_save1(request):
    queryBrand = request.GET.get('brand', '')
    print("queryBrand "+ queryBrand)
    products = []
    try:
       if queryBrand == "hm":
       ## products = getHmProducts()
        products = verifyBrandSupport()
       elif queryBrand == "zara":
        products = getZaraAllProducts()
       elif queryBrand == "asos":
        scrapAsosBrand1()
       elif queryBrand == "vinted":
        products = getFullProfile("https://www.vinted.co.uk/member/136748494-rachg2103")
       return JsonResponse(products, safe=False)

    except Exception as e:
        error_message = "Error during scraping: {}".format(str(e))
        logger.error(error_message)
        return HttpResponse(error_message, status=500)


from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Product
from django.forms.models import model_to_dict

def getSoasProductId(url):
    # Define a regex pattern to match the product ID
    pattern = r'/prd/(\d+)/?'

    # Use re.findall() to search for the product ID in the URL
    match = re.findall(pattern, url)

    # If a match is found, return the product ID
    if match:
        return match[0]
    else:
        return None

def delete_product(product_id):
    try:
        # Get the product instance
        product = Product.objects.all()
        
        # Delete the product
        product.delete()
        
        # Delete associated images
        ProductImage.objects.filter(product=product).delete()
       
    except Product.DoesNotExist:
        error_message = "Product not found:"
        print(error_message)
    
    except Exception as e:
        error_message = "Error deleting product: {}".format(str(e))
        print(error_message)


from subprocess import run
def scrapAsosBrand1():
    try:
        #catUrls = getAsosAllCatUrls()
        url = "https://www.asos.com/asos-design/asos-design-square-neck-pleat-bust-midi-pencil-dress-in-deep-green/prd/205193080#colourWayId-205193081"
        #getAsosProduct1(url)
        scrape_top_news()
        #scrape_hacker_news()
    

    #     headers = {
    #             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    #             'Accept-Language': 'en-US,en;q=0.9',
    #             'Accept-Encoding': 'gzip, deflate, br',
    #             'Connection': 'keep-alive',
    #         }
        
    #     r = requests.get(url, headers=headers)
    #     r.raise_for_status()  # Raise HTTPError for bad responses

    #     ##r = requests.get(url)
    #     soup = BeautifulSoup(r.content, 'html.parser')

    #     headings = soup.find(class_='jcdpl').text
    #     print("beautifull   product name"+ headings)
    except Exception as e:
             print("Error saving product:", str(e))




    #for catUrl in catUrls:
    #     catProductsUrls= getAsosCatAllProductsUrls(catUrl)
    #     for catProductsUrl in catProductsUrls:
    #         getAsosProduct1(catProductsUrl)
    



def getAsosProduct1(productUrl):
    try:
        # Scraping data
        print("url", productUrl)
        soup = getSoap(productUrl)
        #print("soup", soup)
        delete_product(getSoasProductId(productUrl))
        # Creating a new Product instance
        product = Product()
        
        # Populating fields with scraped data
        product.p_id = getSoasProductId(productUrl)
        product.brand = "ASOS"
        product.condition = "Brand new"
        #print(soup.text)
        product.name = soup.find(class_='jcdpl').text
        print(soup.text)
      
        
        product.price = string_to_float(soup.find(class_='MwTOW').getText())
        product.currency_sign = "£"

       
        rating_detail = soup.find(class_='JO8_V').text.split("(")
        product.rating = float(rating_detail[0])
        product.total_rating = int(rating_detail[1].replace(")", ""))
        
        product.description = "Description"
        product.shipping_exchanges_returns = ""
        product.payment_options = ""
        product.views = 0
        # product.colors = []
        # product.sizes = []
        
        # Save the product to the database
        product.save()

        # Scraping images
        e_pictures = soup.find_all("div", class_='fullImageContainer')

        for cat_url in e_pictures:
            image_tag = cat_url.find("img", class_='img')
            if image_tag:
                image_src = image_tag.get('src')
                #pictures.append(image_src)  # Append source URL of image
        #product.pictures = pictures
                product_image = ProductImage(product=product, image_url=image_src)
                product_image.save()
        
        # Adding additional data
       
        
       # print("Product saved successfully."+product.name)
        
    except Exception as e:
        print("Error saving product:", str(e))




from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Product
from django.forms.models import model_to_dict

def get_products1(request):
    try:
        # Parse request parameters
        page = int(request.GET.get('page', 1))
        size = int(request.GET.get('size', 10))
        
        # Calculate skip value for pagination
        skip = (page - 1) * size
        
        # Build query based on request parameters
        query = {}
        for key, value in request.GET.items():
            if key in ['page', 'size']:  # Skip pagination parameters
                continue
            elif key in ['price', 'rating', 'total_rating', 'views']:
                query[key] = float(value)
            elif key == 'search':
                query['name__icontains'] = value  # Search by product name (case-insensitive)
            else:
                query[key + '__icontains'] = value  # Case-insensitive matching for other fields
        
        # Query products based on the constructed query
        products = Product.objects.all() #Product.objects.filter(**query).order_by('-uploaded_date')[skip:skip+size]
        
        # Get total count of products matching the query
        total_count = Product.objects.filter(**query).count()
        
        # Calculate total number of pages
        total_pages = (total_count + size - 1) // size
        
        serialized_products = []
        for product in products:
            # Get associated images for the product
            serialized_product = model_to_dict(product)
            product_images = ProductImage.objects.filter(product=product)
            serialized_product["images"] = list(product_images.values())
            serialized_products.append(serialized_product)
       # products_values = products.values()



       # serialized_products = list(products_values)




        # Metadata about the page
        meta = {
            "page": page,
            "size": size,
            "total_pages": total_pages,
            "total_items": total_count
        }

        response = {
            "products": serialized_products,
            "meta": meta
        }

        return JsonResponse(response, safe=False)
    
    except Exception as e:
        error_message = "Error retrieving products: {}".format(str(e))
        print(error_message)
        return JsonResponse({"error": error_message}, status=500)



# from django.http import JsonResponse
# from scrapy.crawler import CrawlerProcess
# from .hacker_news_spider import HackerNewsSpider

# def scrape_hacker_news():
#     process = CrawlerProcess(settings={
#         "FEEDS": {
#             "items.json": {"format": "json"},
#         },
#     })
#     process.crawl(HackerNewsSpider)
#     process.start()
#     with open("items.json", "r") as f:
#         data = f.read()
#     print(data)
#     return JsonResponse(data, safe=False)



from django.http import JsonResponse
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_top_news(request):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)

    wait = WebDriverWait(driver, 10)
    driver.get('https://news.ycombinator.com/')
    element_list = wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".title > a"))
    )

    news = []
    for element in element_list:
        try:
            title = element.text
            url = element.get_attribute('href')
            news.append({"title": title, "url": url})
        except Exception as e:
            print(e)

    driver.quit()
    print(news)
    return JsonResponse(news, safe=False)


