import scrapy

# class HackerNewsSpider(scrapy.Spider):
#     name = "hacker_news1"
#     start_urls = [
#         "https://www.asos.com/women/dresses/cat/?cid=8799"
#     ]
#     def parse(self, response):
#         print(response.text)
#         for article in response.css("article.productTile_U0clN"):

#             yield {
#                 "title": article.css("p.productDescription_sryaw::text").get(), 
#                 "price": article.css("span.price__B9LP::text").get(), 
                
#             }
#         next_page = response.css("a.morelink::attr(href)").get()
#         if next_page is not None:
#             yield response.follow(next_page, self.parse)



class HackerNewsSpider(scrapy.Spider):
    name = "hacker_news"
    start_urls = [
        "https://www.asos.com/sister-jane/sister-jane-puff-sleeve-ruffle-hem-midaxi-dress-in-powder-pink/prd/205912755#colourWayId-205912756"
    ]
    
    # def start_requests(self):
    #     url = "https://www.asos.com/sister-jane/sister-jane-puff-sleeve-ruffle-hem-midaxi-dress-in-powder-pink/prd/205912755#colourWayId-205912756"
    #     yield SplashRequest(url=url, callback=self.parse, wait=0.5)  # Wait 0.5 seconds after rendering

    def parse(self, response):
        print(response.text)
        for section in response.css("section.layout-aside"):
            # image_url = response.css("div.fullImageContainer img.img::attr(src)").get()
            # price = response.css("span[data-testid='current-price']::text").get()
            yield {
                 "image1": section.css("div.layout-width::text").getall(),
                "title1": section.css("h1.jcdpl::text").get(), 
                # "price": price,
              
                
            }
        next_page = response.css("a.morelink::attr(href)").get()
        if next_page is not None:
            yield response.follow(next_page, self.parse)
            
