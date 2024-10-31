# -*- coding: utf-8 -*-
"""LLM_QA.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1_MVp14lHAUe-Wr3vciGgtPPVEeUo3RDk
"""

from google.colab import drive
drive.mount('/content/drive')
# shared_files = drive.ListFile({'q': "'root' in parents and sharedWithMe=true"}).GetList()
!ls "/content/drive/MyDrive"

!pip install huggingface-hub
!pip install bert_score
!huggingface-cli login --token=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
!huggingface-cli download TheBloke/Mistral-7B-OpenOrca-GGUF mistral-7b-openorca.Q4_K_M.gguf --local-dir . --local-dir-use-symlinks False



!pip install evaluate==0.4.3
!pip install llama-cpp-python==0.1.9
!pip install pinecone-client==5.0.1
!pip install langchain_community==0.2.16
!pip install langchain-chroma==0.1.4
!pip install chromadb==0.5.11
!pip install sentence-transformers==3.1.1
!pip install --upgrade vllm
!pip install --upgrade mistral_common
!pip install gradio
!pip install ctransformers


from sentence_transformers import SentenceTransformer
import chromadb
import re
import os
import pandas as pd
import csv
from tqdm import tqdm
from vllm import LLM
from vllm.sampling_params import SamplingParams

class Embedder():
   def __init__(self):
    pass

   def encode(self):
    pass


   def __call__(self, input):
    input = self.model.encode(input).tolist()
    return input

class SentenceEmbedder(Embedder):
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
       self.model = SentenceTransformer(model_name)
    def get_embedding(self, sent):
        # Метод для получения модели эмбеддингов, которая будет использоваться для векторизации текстов
        return self.model.encode(sent).tolist()
    def __call__(self, input):
        return self.get_embedding(input)

class Collector:
    def add(self, texts: list[str], metadatas: list[dict]):
      pass

    def add_from_directory(self, dir_path: str):
      pass

    def get(self, search_strings: list[str], n_results: int) -> list:
      pass

    def get_documents(self, search_string: str, n_results: int, score_threshold: float) -> list:
      pass

    def clear(self):
      pass

class ChromaCollector(Collector):
  def __init__(self, name, root_path, embeddnig_fn, distance_fn):
    self.client = chromadb.PersistentClient(path=root_path)
    self.distance_fn = distance_fn
    self.embedding_fn = embeddnig_fn
    self.collection = self.client.get_or_create_collection(name=name,
                                                      metadata={"hnsw:space": self.distance_fn},
                                                      embedding_function=self.embedding_fn)

  def add(self, texts: list[str], metadatas: list[dict], ids: list[int]):
    self.collection.add(
      documents=texts,
      metadatas=metadatas,
      ids=ids
    )

  def clear(self):
    self.client.reset()



# init some stuff
path = "/content/drive/My Drive/nlp_itmo/assets/db"
embedder = SentenceEmbedder()
database = ChromaCollector("my_db", path, embedder, "cosine")
message = "The youngest billionaire"
database.collection.query(query_embeddings=embedder(message), n_results=20)["documents"]

from ctransformers import AutoModelForCausalLM
import gradio as gr

llm = AutoModelForCausalLM.from_pretrained("TheBloke/Mistral-7B-OpenOrca-GGUF",
                                           model_file="mistral-7b-openorca.Q4_K_M.gguf",
                                           model_type="mistral", gpu_layers=50)



def process_request(message):
    context = "\n".join(database.collection.query(query_embeddings=embedder(message),
                                                  # 512 tokens for context window is very limiting
                                                  n_results=8)["documents"][0])
    prompt = "Answer the question about the movies using provided context which contains relevant information. It takes priority over other information.\n"
    prompt += "Context: " + context + "\n"
    prompt += "Question: " + message + "\n\n"
    prompt += "Answer: "
    answer = llm(prompt)
    return f"{prompt}{answer}", answer

prompts = [
    "Who are heavyweight champions in the Rocky franchise",
    "What is vibranium?",
    "Who is the youngest billionaire",
    "Who are the enemies of James Bond",
    "What roles does Christoph Waltz play",
    "What are the seven deadly sins",
    "What's inside a black hole",
    "Is the brass top spinning",
    "Can Leutenant Kaffee handle the truth",
    "Who is Darth Vader",
    "Recommend a fun comedy spy movie",
]

answers = [
    "Apollo Creed, Tommy Gunn and Rocky himself. Also Adonis Creed in legacy sequels",
    "Strong fictional metal in Marvel Cinematic Universe. Basically magic",
    "Mark Zuckerberg",
    "There are many, including Goldfinger, Le Chiffre and Spectre",
    "Dr. King Schulz, a bounty hunter, and SS Colonel Hans Landa",  # I think I gaslit OpenOrca into thinking that Christoph Waltz was in Being John Malkovich
    "Gluttony, Sloth, Greed, Wrath, Envy, Lust, and Pride",
    "Singularity. Also laws of physics no longer work. Sometimes time travel",
    "Yes, it is spinning in the last frame of the movie. The directir said it doesn't matter",
    "Yes, he can, he wins the in the court by provoking colonel Jessep",
    "Ex-jedi, Sith lord, father of two",
    "I recommend Kingsman: the secret service, Johnny English, Austin Powers movies"
]
model_answers = []
for prompt in prompts:
  result=process_request(prompt)
  print(result[0])
  print("\n\n")
  model_answers.append(result[1])

from evaluate import load
bertscore = load("bertscore")
predictions = model_answers
references = answers
results = bertscore.compute(predictions=predictions, references=references, lang="en")

results