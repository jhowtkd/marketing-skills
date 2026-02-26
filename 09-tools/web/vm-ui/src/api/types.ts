export type Brand = {
  brand_id: string;
  name: string;
};

export type BrandsResponse = {
  brands: Brand[];
};

export type Project = {
  project_id: string;
  brand_id: string;
  name: string;
  objective?: string | null;
  channels?: string[];
  due_date?: string | null;
};

export type ProjectsResponse = {
  projects: Project[];
};

export type Thread = {
  thread_id: string;
  project_id: string;
  brand_id: string;
  title: string;
  status?: string;
  modes?: string[];
};

export type ThreadsResponse = {
  threads: Thread[];
};

