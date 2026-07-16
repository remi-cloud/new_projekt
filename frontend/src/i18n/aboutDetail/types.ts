import type { AboutTopicSlug } from '../aboutTopics'

export interface AboutDetailSection {
  title: string
  body: string
}

export interface AboutDetailTopic {
  eyebrow: string
  title: string
  intro: string
  sections: AboutDetailSection[]
  inAppTitle: string
  inAppBody: string
}

export interface AboutDetailBundle {
  back: string
  learnMore: string
  notFound: string
  howItWorks: string
  topics: Record<AboutTopicSlug, AboutDetailTopic>
}
